from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
from pathlib import Path

from orchestrator import CommissionSQLOrchestrator

app = FastAPI(title="Commission SQL Generator", version="1.0.0")

# Mount static files for templates
app.mount("/static", StaticFiles(directory="templates"), name="static")

class SRFRequest(BaseModel):
    srf_text: str
    target_tables: Optional[str] = None
    table_schemas: Optional[Dict[str, Any]] = None
    openai_api_key: Optional[str] = None

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
