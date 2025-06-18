"""
Web Application - FastAPI দিয়ে web interface
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

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
        result = assistant.generate_sql_for_srf(
            request.srf_text, 
            request.supporting_info
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
    return {"status": "healthy", "service": "Commission AI Assistant"}

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
