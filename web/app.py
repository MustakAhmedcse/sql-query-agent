"""
Web Application - FastAPI দিয়ে web interface
"""
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import sys
import uvicorn
import time
import json
import subprocess
import logging
from dotenv import load_dotenv
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Import file processor
from file_processor import FileProcessor

# FastAPI app
app = FastAPI(
    title="Commission AI Assistant",
    description="AI-powered SQL generation for BL Commission reports",
    version="1.0.0"
)

# Templates (fix path for web directory)
import os
template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

# Global assistant instance
assistant = None

# Pydantic models
class SRFRequest(BaseModel):
    srf_text: str
    target: Optional[str] = None  # Optional target table structure

class SQLResponse(BaseModel):
    success: bool
    generated_sql: str = None
    error: str = None
    context_quality: dict = None
    validation: dict = None
    similar_examples_count: int = 0
    high_confidence_count: int = 0
    generation_time: float = 0.0
    ai_provider: str = ""
    model_used: str = ""
    srf_history: list = []  # SRF examples used for generation

class FileUploadResponse(BaseModel):
    success: bool
    text: str = ""
    error: str = ""
    file_type: str = ""
    sheet_names: list = []
    requires_sheet_selection: bool = False

class ExcelDataResponse(BaseModel):
    success: bool
    text: str = ""
    html: str = ""
    error: str = ""
    info: dict = None

class ConfigResponse(BaseModel):
    ai_provider: str
    models: dict  # Contains openai and ollama model lists
    current_model: str

class UpdateConfigRequest(BaseModel):
    ai_provider: str = ""
    openai_model: str = ""
    ollama_model: str = ""

class AddSRFSQLRequest(BaseModel):
    srf: str
    sql: str

class AddSRFSQLResponse(BaseModel):
    success: bool
    message: str = ""
    error: str = ""

# Initialize assistant
@app.on_event("startup")
async def startup_event():
    global assistant
    try:
        # Import here to avoid circular imports
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from main import CommissionAIAssistant
        
        assistant = CommissionAIAssistant()
        
        # Try to initialize with existing data
        base_dir = os.path.dirname(os.path.dirname(__file__))  # Go up two levels from web/app.py
        processed_file = os.path.join(base_dir, "data", "training_data", "processed_training_data.json")
        
        if os.path.exists(processed_file):
            print("🚀 Initializing AI Assistant...")
            assistant.initialize_system()
        else:
            print(f"⚠️  No training data found at: {processed_file}")
            print("Please process your data first.")
            
    except Exception as e:
        print(f"❌ Startup error: {str(e)}")
        assistant = None

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/add-training-data", response_class=HTMLResponse)
async def add_training_data_page(request: Request):
    """Add training data page"""
    return templates.TemplateResponse("add_training_data.html", {"request": request})

@app.get("/training-data", response_class=HTMLResponse)
async def manage_training_data_page(request: Request):
    """Manage training data page"""
    return templates.TemplateResponse("manage_training_data.html", {"request": request})

@app.post("/api/generate-sql", response_model=SQLResponse)
async def generate_sql(request: SRFRequest):
    """Generate SQL from SRF"""
    global assistant
    
    if not assistant or not assistant.is_initialized:
        raise HTTPException(
            status_code=503, 
            detail="AI Assistant not initialized. Please check system status."
        )
    
    if not request.srf_text.strip():
        raise HTTPException(status_code=400, detail="SRF text is required")
    
    try:
        import time
        start_time = time.time()
        
        result = assistant.generate_sql_for_srf(
            request.srf_text,
            request.target
        )
        
        end_time = time.time()
        generation_time = round(end_time - start_time, 2)
          # Add timing and AI info to result
        result['generation_time'] = generation_time
        current_provider = os.getenv("AI_PROVIDER", "openai")
        result['ai_provider'] = current_provider
        
        if current_provider == "openai":
            result['model_used'] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif current_provider == "ollama":
            result['model_used'] = os.getenv("OLLAMA_MODEL", "qwen3")
        else:
            result['model_used'] = "unknown"
        
        # Extract SRF history from context
        srf_history = []
        context = result.get('context', {})
        
        # Get similar examples from the context
        similar_examples = context.get('similar_examples', [])
        if not similar_examples:
            # Fallback to all_similar if no high confidence examples
            similar_examples = context.get('all_similar', [])[:5]  # Limit to top 5
        
        for example in similar_examples:
            history_item = {
                'srf_text': example.get('srf_text', ''),
                'sql_query': example.get('sql_query', ''),
                'similarity_score': round(example.get('similarity_score', 0), 3),
                'metadata': example.get('metadata', {})
            }
            srf_history.append(history_item)
        
        # Add SRF history to the result
        result['srf_history'] = srf_history
        
        return SQLResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get system status"""
    global assistant
    
    if not assistant:
        return {
            "status": "not_initialized",
            "message": "AI Assistant not loaded"
        }
    
    status = assistant.get_system_status()
    return status

@app.post("/api/initialize")
async def initialize_system(jsonl_path: str = None):
    """Initialize or reinitialize the system"""
    global assistant
    
    try:
        if not assistant:
            from main import CommissionAIAssistant
            assistant = CommissionAIAssistant()
        
        success = assistant.initialize_system(jsonl_path)
        
        if success:
            return {"success": True, "message": "System initialized successfully"}
        else:
            return {"success": False, "message": "System initialization failed"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reinitialize")
async def reinitialize_system():
    """Reinitialize the system with updated training data"""
    global assistant
    
    try:
        if not assistant:
            from main import CommissionAIAssistant
            assistant = CommissionAIAssistant()
        
        success = assistant.initialize_system()
        
        if success:
            return {"success": True, "message": "System reinitialized successfully with updated training data"}
        else:
            return {"success": False, "message": "System reinitialization failed"}
            
    except Exception as e:
        logger.error(f"Error reinitializing system: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reinitialize system: {str(e)}")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Commission AI Assistant is running"}

# Configuration endpoints
@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get current AI configuration"""
    # Import settings fresh to get updated environment variables
    import importlib
    from config import settings
    importlib.reload(settings)
    
    # Get current values directly from environment
    current_ai_provider = os.getenv("AI_PROVIDER", "openai").lower()
    current_openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    current_ollama_model = os.getenv("OLLAMA_MODEL", "qwen3")
    
    # Determine current model based on provider
    current_model = ""
    if current_ai_provider == "openai":
        current_model = current_openai_model
    elif current_ai_provider == "ollama":
        current_model = current_ollama_model
    
    return ConfigResponse(
        ai_provider=current_ai_provider,
        models={
            "openai": settings.Settings.OPENAI_MODELS,
            "ollama": settings.Settings.OLLAMA_MODELS
        },
        current_model=current_model
    )

@app.post("/api/update-config")
async def update_config(config: UpdateConfigRequest):
    """Update AI provider and model configuration"""
    global assistant
    
    try:        # Update environment variables
        if config.ai_provider:
            os.environ["AI_PROVIDER"] = config.ai_provider
            # Also update the .env file to persist the change
            update_env_file("AI_PROVIDER", config.ai_provider)
        
        if config.openai_model:
            os.environ["OPENAI_MODEL"] = config.openai_model
            update_env_file("OPENAI_MODEL", config.openai_model)
            
        if config.ollama_model:
            os.environ["OLLAMA_MODEL"] = config.ollama_model
            update_env_file("OLLAMA_MODEL", config.ollama_model)
          # Reinitialize the SQL generator if assistant is available
        if assistant and assistant.is_initialized:
            from sql_generator import SQLGenerator
            
            current_provider = os.getenv("AI_PROVIDER", "openai")
            
            if current_provider == "openai":
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    assistant.sql_generator = SQLGenerator(
                        ai_provider="openai",
                        api_key=openai_key,
                        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                    )
                else:
                    raise HTTPException(status_code=400, detail="OpenAI API key not configured")
            elif current_provider == "ollama":
                assistant.sql_generator = SQLGenerator(
                    ai_provider="ollama",
                    model_name=os.getenv("OLLAMA_MODEL", "qwen3"),
                    ollama_base_url=os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")                )
            else:
                raise HTTPException(status_code=400, detail="Invalid AI provider. Only 'openai' and 'ollama' are supported.")
        
        return {
            "success": True,
            "message": f"Configuration updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# File upload endpoints
@app.post("/api/upload-srf", response_model=FileUploadResponse)
async def upload_srf_file(file: UploadFile = File(...)):
    """Upload SRF document file (.doc/.docx)"""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.doc', '.docx')):
            raise HTTPException(
                status_code=400,
                detail="Only .doc and .docx files are supported for SRF content"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Process file
        result = FileProcessor.process_uploaded_file(file.filename, file_content)
        
        if result['success']:
            if result.get('type') == 'excel':
                # This shouldn't happen for SRF files, but handle it
                return FileUploadResponse(
                    success=False,
                    error="Excel files should be uploaded as supporting information, not SRF content"
                )
            else:
                # Document file processed successfully

                result = assistant.cleaned_srf_text(result.get('text', ''))
                if result['success'] is False:
                    return FileUploadResponse(
                        success=False,
                        error=result.get('error', 'Failed to clean SRF text')
                    )
                
                return FileUploadResponse(
                    success=True,
                    text=result.get('response', ''),
                    file_type='document'
                )
        else:
            return FileUploadResponse(
                success=False,
                error=result.get('error', 'Unknown error processing file')
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-supporting", response_model=FileUploadResponse)
async def upload_supporting_file(file: UploadFile = File(...)):
    """Upload supporting information file (.xlsx/.xls/.csv)"""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(
                status_code=400,
                detail="Only .xlsx, .xls, and .csv files are supported for supporting information"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Process file
        result = FileProcessor.process_uploaded_file(file.filename, file_content)
        
        if result['success']:
            if result.get('type') == 'excel':
                # Automatically read the first sheet and return column names
                excel_result = FileProcessor.extract_data_from_excel(file_content, max_rows=0)
                if excel_result['success']:
                    column_names = excel_result.get('info', {}).get('column_names', [])
                    column_info = f"temp_table shared by B2C with data from first sheet\n{', '.join(column_names)}"
                    
                    return FileUploadResponse(
                        success=True,
                        text=column_info,
                        file_type='excel_columns'
                    )
                else:
                    return FileUploadResponse(
                        success=False,
                        error=excel_result.get('error', 'Error reading Excel columns')
                    )
            elif result.get('type') == 'csv':
                # Process CSV immediately
                csv_result = FileProcessor.extract_data_from_csv(file_content, max_rows=1)
                if csv_result['success']:
                    column_names ="temp_table shared by B2C with data \n" +", ".join(csv_result.get('info', {}).get('column_names', []))
                    return FileUploadResponse(
                        success=True,
                        text=column_names,
                        file_type='csv'
                    )
                else:
                    return FileUploadResponse(
                        success=False,
                        error=csv_result.get('error', 'Error processing CSV file')
                    )
        else:
            return FileUploadResponse(
                success=False,
                error=result.get('error', 'Unknown error processing file')
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract-excel-data", response_model=ExcelDataResponse)
async def extract_excel_data(
    file: UploadFile = File(...),
    sheet_name: str = Form(...)
):
    """Extract data from specific Excel sheet"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Extract data from specified sheet
        result = FileProcessor.extract_data_from_excel(
            file_content, 
            sheet_name=sheet_name, 
            max_rows=5
        )
        
        if result['success']:
            return ExcelDataResponse(
                success=True,
                text=result.get('text', ''),
                html=result.get('html', ''),                info=result.get('info', {})
            )
        else:
            return ExcelDataResponse(
                success=False,
                error=result.get('error', 'Error extracting Excel data')
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-srf-sql", response_model=AddSRFSQLResponse)
async def add_srf_sql_pair(request: AddSRFSQLRequest):
    """Add new SRF-SQL pair to the training data and regenerate embeddings"""
    global assistant
    
    try:
        if not request.srf.strip():
            raise HTTPException(status_code=400, detail="SRF text is required")
        
        if not request.sql.strip():
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        # Path to the JSONL file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)  # Create data directory if it doesn't exist
        jsonl_file_path = os.path.join(data_dir, "srf_sql_pairs.jsonl")
        
        # Create the new entry
        new_entry = {
            "srf": request.srf.strip(),
            "sql": request.sql.strip(),
            "enabled": True
        }
        
        # Append to the JSONL file
        with open(jsonl_file_path, 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps(new_entry, ensure_ascii=False) + '\n')
        
        # Automatically run the setup command to regenerate embeddings
        print("🔄 Running setup command to regenerate embeddings with new training data...")
        
        try:
            import subprocess
            import sys
            
            # Run the setup command using subprocess
            run_py_path = os.path.join(base_dir, "run.py")
            result = subprocess.run(
                [sys.executable, run_py_path, "setup"],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ Setup command completed successfully")
                
                return AddSRFSQLResponse(
                    success=True,
                    message="SRF-SQL pair added and embeddings regenerated. Please reinitialize the system to apply changes."
                )
            else:
                print(f"❌ Setup command failed with return code {result.returncode}")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                
                return AddSRFSQLResponse(
                    success=True,
                    message="SRF-SQL pair added successfully, but automatic embedding regeneration failed. Please run 'python run.py setup' manually."
                )
                
        except subprocess.TimeoutExpired:
            return AddSRFSQLResponse(
                success=True,
                message="SRF-SQL pair added successfully, but embedding regeneration is taking too long. Please run 'python run.py setup' manually."
            )
        except Exception as setup_error:
            print(f"❌ Error running setup command: {str(setup_error)}")
            return AddSRFSQLResponse(
                success=True,
                message=f"SRF-SQL pair added successfully, but automatic setup failed: {str(setup_error)}. Please run 'python run.py setup' manually."
            )
        
    except Exception as e:
        return AddSRFSQLResponse(
            success=False,
            error=str(e)
        )

@app.get("/api/training-stats")
async def get_training_stats():
    """Get training data statistics"""
    try:
        # Path to the JSONL file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        jsonl_file_path = os.path.join(base_dir, "data", "srf_sql_pairs.jsonl")
        
        if not os.path.exists(jsonl_file_path):
            return {
                "total_pairs": 0,
                "file_size": 0,
                "last_modified": None
            }
        
        # Count lines in JSONL file
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f if line.strip())
        
        # Get file stats
        file_stats = os.stat(jsonl_file_path)
        file_size = file_stats.st_size
        last_modified = file_stats.st_mtime
        
        return {
            "total_pairs": line_count,
            "file_size": file_size,
            "last_modified": last_modified
        }
        
    except Exception as e:
        return {
            "total_pairs": 0,
            "file_size": 0,
            "last_modified": None,
            "error": str(e)
        }

@app.get("/api/training-data")
async def get_training_data(page: int = 1, limit: int = 10, search: str = ""):
    """Get paginated list of training data with optional search"""
    try:
        # Path to the JSONL file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        jsonl_file_path = os.path.join(base_dir, "data", "srf_sql_pairs.jsonl")
        
        if not os.path.exists(jsonl_file_path):
            return {
                "data": [],
                "total": 0,
                "page": page,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            }
        
        # Read all entries and filter by search
        entries = []
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    
                    # Apply search filter
                    if search:
                        search_lower = search.lower()
                        srf_content = entry.get('srf', '').lower()
                        sql_content = entry.get('sql', '').lower()
                        
                        # Skip if search term not found in either srf or sql
                        if search_lower not in srf_content and search_lower not in sql_content:
                            continue
                    
                    # Add ID and preview for list view
                    entry['id'] = line_num
                    entry['enabled'] = entry.get('enabled', True)  # Default to enabled if not specified
                    entry['srf_preview'] = entry.get('srf', '')[:200] + '...' if len(entry.get('srf', '')) > 200 else entry.get('srf', '')
                    entry['sql_preview'] = entry.get('sql', '')[:200] + '...' if len(entry.get('sql', '')) > 200 else entry.get('sql', '')
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        # Calculate pagination
        total = len(entries)
        total_pages = (total + limit - 1) // limit
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        # Get paginated data
        paginated_data = entries[start_idx:end_idx]
        
        return {
            "data": paginated_data,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except Exception as e:
        logger.error(f"Error getting training data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get training data: {str(e)}")

@app.get("/api/training-data/{item_id}")
async def get_training_data_detail(item_id: int):
    """Get detailed view of a specific training data item"""
    try:
        # Path to the JSONL file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        jsonl_file_path = os.path.join(base_dir, "data", "srf_sql_pairs.jsonl")
        
        if not os.path.exists(jsonl_file_path):
            raise HTTPException(status_code=404, detail="Training data file not found")
        
        # Read and find the specific entry
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line_num == item_id:
                    try:
                        entry = json.loads(line.strip())
                        entry['id'] = line_num
                        return entry
                    except json.JSONDecodeError:
                        raise HTTPException(status_code=400, detail="Invalid JSON in training data")
        
        raise HTTPException(status_code=404, detail="Training data item not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting training data detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get training data detail: {str(e)}")

@app.delete("/api/training-data/{item_id}")
async def delete_training_data(item_id: int):
    """Delete a specific training data item"""
    try:
        # Path to the JSONL file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        jsonl_file_path = os.path.join(base_dir, "data", "srf_sql_pairs.jsonl")
        
        if not os.path.exists(jsonl_file_path):
            raise HTTPException(status_code=404, detail="Training data file not found")
        
        # Read all entries
        entries = []
        deleted_entry = None
        
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    if line_num == item_id:
                        deleted_entry = entry
                    else:
                        entries.append(entry)
                except json.JSONDecodeError:
                    # Keep invalid lines as they were (just skip them)
                    if line_num != item_id:
                        entries.append({"invalid_line": line.strip()})
        
        if deleted_entry is None:
            raise HTTPException(status_code=404, detail="Training data item not found")
        
        # Write back the remaining entries
        with open(jsonl_file_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                if "invalid_line" in entry:
                    f.write(entry["invalid_line"] + '\n')
                else:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        # Run setup command to regenerate embeddings
        try:
            current_dir = os.path.dirname(os.path.dirname(__file__))
            result = subprocess.run([
                sys.executable, 'run.py', 'setup'
            ], 
            cwd=current_dir,
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Setup command completed successfully after deletion")
                setup_success = True
                setup_message = "Training data deleted and embeddings regenerated. Please reinitialize the system to apply changes."
            else:
                logger.error(f"Setup command failed: {result.stderr}")
                setup_success = False
                setup_message = f"Training data deleted but setup failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            logger.error("Setup command timed out")
            setup_success = False
            setup_message = "Training data deleted but setup process timed out. Please run 'python run.py setup' manually."
        except Exception as setup_error:
            logger.error(f"Setup command error: {setup_error}")
            setup_success = False
            setup_message = f"Training data deleted but setup failed: {str(setup_error)}"
        
        return {
            "success": True,
            "message": setup_message,
            "setup_success": setup_success,
            "deleted_item": deleted_entry
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting training data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete training data: {str(e)}")

@app.patch("/api/training-data/{item_id}/toggle")
async def toggle_training_data(item_id: int):
    """Toggle enable/disable status of a training data item"""
    try:
        # Path to the JSONL file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        jsonl_file_path = os.path.join(base_dir, "data", "srf_sql_pairs.jsonl")
        
        if not os.path.exists(jsonl_file_path):
            raise HTTPException(status_code=404, detail="Training data file not found")
        
        # Read all entries
        entries = []
        target_entry = None
        
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    if line_num == item_id:
                        # Toggle the enabled status
                        current_status = entry.get('enabled', True)
                        entry['enabled'] = not current_status
                        target_entry = entry
                    entries.append(entry)
                except json.JSONDecodeError:
                    # Keep invalid lines as they were
                    entries.append({"invalid_line": line.strip()})
        
        if target_entry is None:
            raise HTTPException(status_code=404, detail="Training data item not found")
        
        # Write back all entries
        with open(jsonl_file_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                if "invalid_line" in entry:
                    f.write(entry["invalid_line"] + '\n')
                else:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        # Run setup command to regenerate embeddings (only for enabled entries)
        try:
            current_dir = os.path.dirname(os.path.dirname(__file__))
            result = subprocess.run([
                sys.executable, 'run.py', 'setup'
            ], 
            cwd=current_dir,
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Setup command completed successfully after toggle")
                setup_success = True
                setup_message = f"Training data {'enabled' if target_entry['enabled'] else 'disabled'} and embeddings regenerated. Please reinitialize the system to apply changes."
            else:
                logger.error(f"Setup command failed: {result.stderr}")
                setup_success = False
                setup_message = f"Training data toggled but setup failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            logger.error("Setup command timed out")
            setup_success = False
            setup_message = "Training data toggled but setup process timed out. Please run 'python run.py setup' manually."
        except Exception as setup_error:
            logger.error(f"Setup command error: {setup_error}")
            setup_success = False
            setup_message = f"Training data toggled but setup failed: {str(setup_error)}"
        
        return {
            "success": True,
            "message": setup_message,
            "setup_success": setup_success,
            "enabled": target_entry['enabled'],
            "item_id": item_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling training data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle training data: {str(e)}")

def update_env_file(key: str, value: str):
    """Update a key-value pair in the .env file"""
    try:
        env_file_path = ".env"
        
        # Read current .env file
        lines = []
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
        
        # Update or add the key
        key_found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break
        
        # If key not found, add it
        if not key_found:
            lines.append(f"{key}={value}\n")
        
        # Write back to file
        with open(env_file_path, 'w') as f:
            f.writelines(lines)
            
    except Exception as e:
        print(f"Error updating .env file: {e}")
        # Don't raise error, just log it

# Run server
def run_web_app():
    """Run the web application"""
    print("🌐 Starting Commission AI Assistant Web App...")
    print("📱 Open http://localhost:8000 in your browser")
    
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    run_web_app()
