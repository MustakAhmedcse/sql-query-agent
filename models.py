from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class SQLStep:
    """Represents a single SQL step in the commission calculation"""
    step_number: int
    name: str
    description: str
    sql_query: str
    depends_on: List[int] = None
    validation_query: Optional[str] = None
    expected_output: Optional[str] = None

class CommissionState(TypedDict):
    """State object for the LangGraph workflow"""
    # Input data
    srf_text: str
    table_schemas: Dict[str, Any]
    
    # Extracted metadata
    metadata: Optional[Dict[str, Any]]
    
    # Generated SQL steps
    sql_steps: List[SQLStep]
    
    # Error handling
    errors: List[str]
    warnings: List[str]
    
    # Final output
    final_script: Optional[str]
    summary_report: Optional[str]

@dataclass
class TableSchema:
    """Represents database table schema"""
    name: str
    columns: List[Dict[str, str]]
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'columns': self.columns,
            'description': self.description
        }
