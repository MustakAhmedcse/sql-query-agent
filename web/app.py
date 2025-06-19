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
    supporting_info: str = ""

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
            request.supporting_info
        )
        
        end_time = time.time()
        generation_time = round(end_time - start_time, 2)
        
        # Add timing and AI info to result
        result['generation_time'] = generation_time
        result['ai_provider'] = os.getenv("AI_PROVIDER", "openai")
        result['model_used'] = (
            os.getenv("OPENAI_MODEL", "gpt-4o-mini") if result['ai_provider'] == "openai"
            else os.getenv("OLLAMA_MODEL", "qwen3") if result['ai_provider'] == "ollama"
            else "template"
        )
        
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
    from config.settings import settings
    
    # Determine current model based on provider
    current_model = ""
    if settings.AI_PROVIDER == "openai":
        current_model = settings.OPENAI_MODEL
    elif settings.AI_PROVIDER == "ollama":
        current_model = settings.OLLAMA_MODEL
    
    return ConfigResponse(
        ai_provider=settings.AI_PROVIDER,
        models={
            "openai": settings.OPENAI_MODELS,
            "ollama": settings.OLLAMA_MODELS,
            "template": []
        },
        current_model=current_model
    )

@app.post("/api/update-config")
async def update_config(config: UpdateConfigRequest):
    """Update AI provider and model configuration"""
    global assistant
    
    try:
        # Update environment variables
        if config.ai_provider:
            os.environ["AI_PROVIDER"] = config.ai_provider
        
        if config.openai_model:
            os.environ["OPENAI_MODEL"] = config.openai_model
            
        if config.ollama_model:
            os.environ["OLLAMA_MODEL"] = config.ollama_model
        
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
                    assistant.sql_generator = SQLGenerator(ai_provider="template")
            elif current_provider == "ollama":
                assistant.sql_generator = SQLGenerator(
                    ai_provider="ollama",
                    model_name=os.getenv("OLLAMA_MODEL", "qwen3"),                    ollama_base_url=os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")
                )
            else:
                assistant.sql_generator = SQLGenerator(ai_provider="template")
        
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
                return FileUploadResponse(
                    success=True,
                    text=result.get('text', ''),
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
                csv_result = FileProcessor.extract_data_from_csv(file_content, max_rows=5)
                if csv_result['success']:
                    return FileUploadResponse(
                        success=True,
                        text=csv_result.get('text', ''),
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
                html=result.get('html', ''),
                info=result.get('info', {})
            )
        else:
            return ExcelDataResponse(
                success=False,
                error=result.get('error', 'Error extracting Excel data')
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration"""
    global assistant
    
    if not assistant:
        raise HTTPException(status_code=503, detail="AI Assistant not initialized")
    
    try:
        config = assistant.get_config()
        return ConfigResponse(**config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config", response_model=ConfigResponse)
async def update_config(request: UpdateConfigRequest):
    """Update configuration settings"""
    global assistant
    
    if not assistant:
        raise HTTPException(status_code=503, detail="AI Assistant not initialized")
    
    try:
        success = assistant.update_config(request.ai_provider, request.model)
        
        if success:
            # Return updated config
            config = assistant.get_config()
            return ConfigResponse(**config)
        else:
            raise HTTPException(status_code=400, detail="Invalid configuration update")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
