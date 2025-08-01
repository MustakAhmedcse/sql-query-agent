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
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Import file processor
from file_processor import FileProcessor

# FastAPI app
app = FastAPI(
    title="Commission AI Assistant",
    description="AI-powered SQL generation for MyBL Commission reports",
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
                return FileUploadResponse(
                    success=True,
                    file_type='excel',
                    sheet_names=result.get('sheet_names', []),
                    requires_sheet_selection=result.get('requires_sheet_selection', False)
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
