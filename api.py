from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from orchestrator import CommissionSQLOrchestrator

# Helper function for cleaning up temporary files
def cleanup_files(file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ Deleted temporary file: {file_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not delete temporary file {file_path}: {e}")

app = FastAPI(title="Commission SQL Generator", version="1.0.0")

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

# Mount static files for templates
app.mount("/static", StaticFiles(directory="templates"), name="static")

class SRFRequest(BaseModel):
    srf_text: str
    target_tables: Optional[str] = None
    table_schemas: Optional[Dict[str, Any]] = None
    openai_api_key: Optional[str] = None

class FileUploadResponse(BaseModel):
    success: bool
    schema_text: Optional[str] = None
    files_processed: Optional[int] = None
    error: Optional[str] = None

# Global orchestrator instance
orchestrator = None

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main interface"""
    html_file = Path("templates/index.html")
    if html_file.exists():
        return FileResponse(html_file)
    else:
        return HTMLResponse(
            content="<h1>Error: Template file not found</h1><p>Please ensure templates/index.html exists.</p>",
            status_code=404
        )

@app.post("/upload-files", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Handle file uploads and generate schema text for Target Tables Structure"""
    uploaded_file_paths = []
    try:
        # Initialize orchestrator (use environment API key for file processing)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return JSONResponse({
                "success": False,
                "error": "OpenAI API key not configured on server"
            }, status_code=400)
        
        file_orchestrator = CommissionSQLOrchestrator(openai_api_key=api_key)
        
        # Save uploaded files temporarily
        for file in files:
            if file.filename:
                # Validate file type
                if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
                    return JSONResponse({
                        "success": False,
                        "error": f"Unsupported file type: {file.filename}. Only CSV and Excel files are allowed."
                    }, status_code=400)
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = os.path.splitext(file.filename)[1]
                temp_filename = f"{timestamp}_{len(uploaded_file_paths)}_{file.filename}"
                file_path = os.path.join("uploads", temp_filename)
                
                # Save file
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                uploaded_file_paths.append(file_path)
        
        if not uploaded_file_paths:
            return JSONResponse({
                "success": False,
                "error": "No valid files uploaded"
            }, status_code=400)
        
        # Generate schema text from uploaded files
        schema_text = file_orchestrator.generate_schema_from_files(uploaded_file_paths)
        
        # Immediately clean up temporary files after processing
        cleanup_files(uploaded_file_paths)
        
        if not schema_text:
            return JSONResponse({
                "success": False,
                "error": "Could not generate schema from uploaded files"
            }, status_code=400)
        
        return JSONResponse({
            "success": True,
            "schema_text": schema_text,
            "files_processed": len(uploaded_file_paths)
        })
        
    except Exception as e:
        # Clean up temporary files in case of error
        cleanup_files(uploaded_file_paths)
        
        return JSONResponse({
            "success": False,
            "error": f"Error processing files: {str(e)}"
        }, status_code=500)

@app.post("/generate-sql")
async def generate_sql(request: SRFRequest):
    """Generate SQL steps from SRF requirements"""
    try:
        global orchestrator
        
        # Initialize orchestrator with API key
        api_key = request.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key is required")
        
        orchestrator = CommissionSQLOrchestrator(openai_api_key=api_key)
        
        # Process SRF
        result = orchestrator.process_srf(
            srf_text=request.srf_text,
            target_tables_text=request.target_tables,
            table_schemas=request.table_schemas
        )
        
        # Convert result to JSON-serializable format
        serializable_state = {
            "srf_text": result["srf_text"],
            "metadata": result["metadata"],
            "sql_steps": [
                {
                    "step_number": step.step_number,
                    "name": step.name,
                    "description": step.description,
                    "sql_query": step.sql_query,
                    "depends_on": step.depends_on,
                    "validation_query": step.validation_query
                }
                for step in result["sql_steps"]
            ],
            "errors": result["errors"],
            "warnings": result["warnings"],
            "final_script": result["final_script"],
            "summary_report": result["summary_report"]
        }
        
        return {
            "success": True,
            "state": serializable_state,
            "message": f"Generated {len(result['sql_steps'])} SQL steps"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
