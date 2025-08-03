from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from models import CommissionState, SQLStep
from sql_generators import MetadataExtractor, SQLStepGenerator
from typing import Dict, Any
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class CommissionSQLOrchestrator:
    """LangGraph-based orchestrator for commission SQL generation"""
    
    def __init__(self, openai_api_key: str = None):
        # Initialize LLM
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL") or "gpt-4o",
            temperature= os.getenv("OPENAI_TEMPERATURE", "0.1"),
            api_key=api_key
        )
        
        # Initialize components
        self.metadata_extractor = MetadataExtractor(self.llm)
        self.sql_generator = SQLStepGenerator(self.llm)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create the state graph
        workflow = StateGraph(CommissionState)
        
        # Add nodes
        workflow.add_node("extract_metadata", self._extract_metadata_node)
        workflow.add_node("generate_sql_steps", self._generate_sql_steps_node)
        workflow.add_node("validate_steps", self._validate_steps_node)
        workflow.add_node("compile_final_script", self._compile_final_script_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # Add edges
        workflow.set_entry_point("extract_metadata")
        workflow.add_edge("extract_metadata", "generate_sql_steps")
        workflow.add_edge("generate_sql_steps", "validate_steps")
        workflow.add_edge("validate_steps", "compile_final_script")
        workflow.add_edge("compile_final_script", "generate_report")
        workflow.add_edge("generate_report", END)
        
        # Compile the graph
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _extract_metadata_node(self, state: CommissionState) -> CommissionState:
        """Node for extracting metadata from SRF"""
        print("🔍 Extracting metadata from SRF...")
        return self.metadata_extractor.extract(state)
    
    def _generate_sql_steps_node(self, state: CommissionState) -> CommissionState:
        """Node for generating SQL steps"""
        print("⚙️ Generating SQL steps...")
        return self.sql_generator.generate_all_steps(state)
    
    def _validate_steps_node(self, state: CommissionState) -> CommissionState:
        """Node for validating generated SQL steps"""
        print("✅ Validating SQL steps...")
        
        try:
            validation_results = {}
            warnings = []
            
            # Check step dependencies
            for step in state["sql_steps"]:
                if step.depends_on:
                    for dep in step.depends_on:
                        if not any(s.step_number == dep for s in state["sql_steps"]):
                            warnings.append(f"Step {step.step_number} depends on missing step {dep}")
            
            # Validate SQL syntax (basic checks)
            for step in state["sql_steps"]:
                if not step.sql_query.strip():
                    warnings.append(f"Step {step.step_number} has empty SQL query")
                elif not any(keyword in step.sql_query.upper() for keyword in ['SELECT', 'CREATE', 'INSERT', 'UPDATE', 'WITH']):
                    warnings.append(f"Step {step.step_number} may not contain valid SQL")
            
            validation_results["dependency_check"] = "PASSED" if not warnings else "WARNING"
            validation_results["warnings"] = warnings
            
            state["validation_results"] = validation_results
            state["warnings"].extend(warnings)
            
        except Exception as e:
            state["errors"].append(f"Validation failed: {str(e)}")
        
        return state
    
    def _compile_final_script_node(self, state: CommissionState) -> CommissionState:
        """Node for compiling final SQL script"""
        print("📝 Compiling final SQL script...")
        
        try:
            script_parts = []
            
            # Add header
            metadata = state["metadata"]
            script_parts.append(f"""
        -- ========================================================================
        -- Commission Calculation Script: {metadata.get('commission_name', 'Unknown')}
        -- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        -- Campaign Period: {metadata.get('start_date')} to {metadata.get('end_date')}
        -- Receiver Channel: {metadata.get('receiver_channel')}
        -- ========================================================================
        """)
            
            # Add each SQL step
            for step in state["sql_steps"]:
                script_parts.append(f"""
        -- ========================================================================
        -- STEP {step.step_number}: {step.name.upper()}
        -- Description: {step.description}
        -- Depends on: {step.depends_on if step.depends_on else 'None'}
        -- ========================================================================

        {step.sql_query}

        -- Validation query for Step {step.step_number}:
        -- {step.validation_query or 'No validation query specified'}

        """)
            
            # Add footer
            script_parts.append("""
        -- ========================================================================
        -- END OF COMMISSION CALCULATION SCRIPT
        -- ========================================================================
        """)
            
            state["final_script"] = "\n".join(script_parts)
            
        except Exception as e:
            state["errors"].append(f"Script compilation failed: {str(e)}")
        
        return state
    
    def _generate_report_node(self, state: CommissionState) -> CommissionState:
        """Node for generating summary report"""
        print("📊 Generating summary report...")
        
        try:
            metadata = state["metadata"]
            steps = state["sql_steps"]
            validation = state["validation_results"]
            
            report_parts = []
            
            # Header
            report_parts.append(f"""
        # Commission SQL Generation Report

        **Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        **Commission Name:** {metadata.get('commission_name', 'Unknown')}
        **Campaign Period:** {metadata.get('start_date')} to {metadata.get('end_date')}

        ## Summary
        - **Total SQL Steps:** {len(steps)}
        - **Validation Status:** {validation.get('dependency_check', 'NOT VALIDATED')}
        - **Warnings:** {len(state['warnings'])}
        - **Errors:** {len(state['errors'])}

        ## Metadata Extracted
        """)
            
            # Add metadata table
            for key, value in metadata.items():
                report_parts.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            
            # Add steps overview
            report_parts.append("\n## SQL Steps Overview\n")
            for step in steps:
                report_parts.append(f"""
        ### Step {step.step_number}: {step.name}
        - **Description:** {step.description}
        - **Dependencies:** {step.depends_on if step.depends_on else 'None'}
        - **SQL Length:** {len(step.sql_query)} characters
        """)
                    
            # Add warnings and errors
            if state["warnings"]:
                report_parts.append("\n## Warnings\n")
                for warning in state["warnings"]:
                    report_parts.append(f"- ⚠️ {warning}")
            
            if state["errors"]:
                report_parts.append("\n## Errors\n")
                for error in state["errors"]:
                    report_parts.append(f"- ❌ {error}")
            
            state["summary_report"] = "\n".join(report_parts)
            
        except Exception as e:
            state["errors"].append(f"Report generation failed: {str(e)}")
        
        return state
    
    def process_srf(self, srf_text: str, target_tables_text: str = None, table_schemas: Dict[str, Any] = None) -> CommissionState:
        """Process SRF and generate SQL commission calculation"""
        
        # Parse target tables from input if provided
        parsed_schemas = {}
        if target_tables_text:
            parsed_schemas = self._parse_target_tables_from_text(target_tables_text)
        
        # Merge with default schemas and any provided schemas
        final_schemas = self._get_default_schemas()
        if table_schemas:
            final_schemas.update(table_schemas)
        if parsed_schemas:
            final_schemas.update(parsed_schemas)
        
        # Initialize state
        initial_state = CommissionState(
            srf_text=srf_text,
            table_schemas=final_schemas,
            metadata=None,
            sql_steps=[],
            errors=[],
            warnings=[],
            final_script=None,
            summary_report=None
        )
        
        # Run the workflow
        config = {"configurable": {"thread_id": "commission_calculation"}}
        result = self.graph.invoke(initial_state, config)
        
        return result

    def _parse_target_tables_from_text(self, target_tables_text: str) -> Dict[str, Any]:
        """Parse target table schemas from user input text"""
        import re
        
        schemas = {}
        
        try:
            # Split by table definitions (look for patterns like "TABLE_NAME:")
            table_blocks = re.split(r'\n(?=[A-Z_][A-Z0-9_]*:)', target_tables_text.strip())
            
            for block in table_blocks:
                if not block.strip():
                    continue
                    
                lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
                if not lines:
                    continue
                    
                # Extract table name from first line
                first_line = lines[0].strip()
                if ':' in first_line:
                    table_name = first_line.replace(':', '').strip().upper()
                    
                    # Parse columns from remaining lines
                    columns = []
                    for line in lines[1:]:
                        line = line.strip()
                        if not line or line.startswith('#') or line.startswith('--'):
                            continue
                            
                        # Remove trailing comma if present
                        if line.endswith(','):
                            line = line[:-1].strip()
                            
                        # Parse column definition: COLUMN_NAME, TYPE[, Description]
                        if ',' in line:
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 2 and parts[0] and parts[1]:
                                col_name = parts[0].upper()
                                col_type = parts[1]
                                col_desc = parts[2] if len(parts) > 2 and parts[2] else col_name.replace('_', ' ').title()
                                
                                columns.append({
                                    "name": col_name,
                                    "type": col_type,
                                    "description": col_desc
                                })
                        else:
                            # Single column name only
                            col_name = line.upper().strip()
                            if col_name and not col_name.startswith('-'):
                                columns.append({
                                    "name": col_name,
                                    "type": "VARCHAR2(100)",
                                    "description": col_name.replace('_', ' ').title()
                                })
                    
                    if columns:
                        schemas[table_name] = {
                            "name": table_name,
                            "columns": columns,
                            "description": f"Target table: {table_name}"
                        }
                        
        except Exception as e:
            print(f"Warning: Could not parse target tables: {e}")
            
        return schemas
    
    def _get_default_schemas(self) -> Dict[str, Any]:
        """Get default table schemas from JSON file"""
        import json
        
        try:
            # Try to read from schemas.json file
            schema_file_path = os.path.join(os.path.dirname(__file__), "schemas.json")
            
            if os.path.exists(schema_file_path):
                with open(schema_file_path, 'r', encoding='utf-8') as f:
                    schemas = json.load(f)
                print(f"📋 Loaded {len(schemas)} schemas from schemas.json")
                return schemas
            else:
                print(f"⚠️ Schema file not found at {schema_file_path}, using fallback schemas")
                return self._get_fallback_schemas()
                
        except Exception as e:
            print(f"⚠️ Error reading schema file: {e}, using fallback schemas")
            return self._get_fallback_schemas()
    
    def _get_fallback_schemas(self) -> Dict[str, Any]:
        """Get fallback table schemas when JSON file is not available"""
        return {
            "EV_RECHARGE_COM_DAILY": {
                "name": "EV_RECHARGE_COM_DAILY",
                "columns": [
                    {"name": "RETAILER_MSISDN", "type": "VARCHAR2(20)", "description": "Retailer MSISDN"},
                    {"name": "SUB_MSISDN", "type": "VARCHAR2(20)", "description": "Subscriber MSISDN"},
                    {"name": "TOP_UP_DATE", "type": "DATE", "description": "Recharge date"},
                    {"name": "RECHARGE_AMOUNT", "type": "NUMBER", "description": "Recharge amount"},
                    {"name": "SERVICE_TYPE", "type": "VARCHAR2(100)", "description": "Service type"}
                ],
                "description": "Daily recharge transaction data"
            },
            "AGENT_LIST_DAILY": {
                "name": "AGENT_LIST_DAILY",
                "columns": [
                    {"name": "TOPUP_MSISDN", "type": "VARCHAR2(26)", "description": "Agent MSISDN"},
                    {"name": "RETAILER_CODE", "type": "VARCHAR2(7)", "description": "Retailer code"},
                    {"name": "DIST_CODE", "type": "VARCHAR2(8)", "description": "Distributor code"},
                    {"name": "REGION_NAME", "type": "VARCHAR2(50)", "description": "Region name"},
                    {"name": "DATA_DATE", "type": "DATE", "description": "Data snapshot date"},
                    {"name": "ENABLED", "type": "CHAR(1)", "description": "Active status"}
                ],
                "description": "Daily agent hierarchy and mapping data"
            }
        }

    def save_output(self, result: CommissionState, output_dir: str = "output"):
        """Save the generated outputs to files"""
        import os
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save final SQL script
        if result["final_script"]:
            with open(f"{output_dir}/commission_calculation.sql", "w") as f:
                f.write(result["final_script"])
        
        # Save summary report
        if result["summary_report"]:
            with open(f"{output_dir}/generation_report.md", "w") as f:
                f.write(result["summary_report"])
        
        # Save metadata as JSON
        if result["metadata"]:
            import json
            with open(f"{output_dir}/extracted_metadata.json", "w") as f:
                json.dump(result["metadata"], f, indent=2)
        
        print(f"📁 Outputs saved to {output_dir}/ directory")

# Usage example
if __name__ == "__main__":
    # Sample SRF text
    sample_srf = """
    Commission Name: Distributor Double Dhamaka Deno Campaign_10th to 15th Aug24
    Start Date: 10-Aug-2024
    End Date: 15-Aug-2024
    Commission Receiver Channel: Distributor
    
    Commission Business Logics:
    - KPI: Deno Recharge
    - Target: DD will be given Deno Recharge targets
    - Mapping: Agent list of 15th Aug'24 will be considered
    - Selected Deno (199, 229, 249, 299, 399, 499, 599, 699, 799, 899) will be considered
    - Upon achieving Selected Deno Recharge target, Distributor will be given incentives
    - Double Dhamaka: Upon achieving all bundle Target, 0.5% additional Incentives
    """
    
    # Initialize orchestrator
    orchestrator = CommissionSQLOrchestrator()
    
    # Process SRF
    result = orchestrator.process_srf(sample_srf)
    
    # Save outputs
    orchestrator.save_output(result)
    
    print("✅ Commission SQL generation completed!")
