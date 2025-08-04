from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from models import CommissionState, SQLStep
from sql_generators import MetadataExtractor, SQLStepGenerator
from typing import Dict, Any
import os
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

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
    
    def process_srf(self, srf_text: str, target_tables_text: str = None, table_schemas: Dict[str, Any] = None, file_paths: list = None) -> CommissionState:
        """Process SRF and generate SQL commission calculation"""
        
        # Parse target tables from different sources
        parsed_schemas = {}
        
        # 1. Parse from uploaded files (highest priority)
        if file_paths:
            file_schemas = self.process_uploaded_files(file_paths)
            parsed_schemas.update(file_schemas)
            print(f"📁 Processed {len(file_schemas)} tables from uploaded files")
        
        # 2. Parse from text input (if no files or additional tables)
        if target_tables_text:
            text_schemas = self._parse_target_tables_from_text(target_tables_text)
            parsed_schemas.update(text_schemas)
            print(f"📝 Parsed {len(text_schemas)} tables from text input")
        
        # Merge with default schemas and any provided schemas
        final_schemas = self._get_default_schemas()
        if table_schemas:
            final_schemas.update(table_schemas)
        if parsed_schemas:
            final_schemas.update(parsed_schemas)
        
        print(f"📋 Total schemas available: {len(final_schemas)}")
        print(f"🎯 Target tables: {[name for name in final_schemas.keys() if 'TARGET' in name or name not in ['EV_RECHARGE_COM_DAILY', 'AGENT_LIST_DAILY']]}")
        
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

    def generate_schema_from_files(self, file_paths: list) -> str:
        """Generate target table schema text from uploaded CSV/Excel files"""
        import pandas as pd
        import os
        
        schema_text_parts = []
        
        try:
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    print(f"⚠️ File not found: {file_path}")
                    continue
                
                # Get file name without extension for table name
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                table_name = file_name.upper().replace(' ', '_').replace('-', '_')
                
                try:
                    # Read the file (first sheet for Excel)
                    if file_path.lower().endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(file_path, sheet_name=0, nrows=1)  # Read first row to infer types
                        df_full = pd.read_excel(file_path, sheet_name=0, nrows=10)  # Read more rows for better type inference
                    elif file_path.lower().endswith('.csv'):
                        df = pd.read_csv(file_path, nrows=1)  # Read first row
                        df_full = pd.read_csv(file_path, nrows=10)  # Read more rows for better type inference
                    else:
                        print(f"⚠️ Unsupported file format: {file_path}")
                        continue
                    
                    if df.empty:
                        print(f"⚠️ Empty file: {file_path}")
                        continue
                    
                    # Generate schema for this table
                    schema_text_parts.append(f"{table_name}")
                    
                    for column_name in df.columns:
                        # Clean column name
                        clean_col_name = str(column_name).upper().replace(' ', '_').replace('-', '_')
                        
                        # Infer data type from the sample data
                        col_type = self._infer_column_type(df_full[column_name])
                        
                        # Add column to schema
                        schema_text_parts.append(f"{clean_col_name}, {col_type},")
                    
                    # Add empty line between tables
                    schema_text_parts.append("")
                    
                    print(f"✅ Generated schema for: {table_name} ({len(df.columns)} columns)")
                    
                except Exception as e:
                    print(f"⚠️ Error processing file {file_path}: {str(e)}")
                    continue
            
            return "\n".join(schema_text_parts)
            
        except Exception as e:
            print(f"❌ Error generating schema from files: {str(e)}")
            return ""
    
    def _infer_column_type(self, column_series) -> str:
        """Infer Oracle data type from pandas column data"""
        try:
            # Remove null values for type inference
            non_null_series = column_series.dropna()
            
            if non_null_series.empty:
                return "VARCHAR2(100)"
            
            # Check if it's numeric
            if pd.api.types.is_numeric_dtype(non_null_series):
                # Check if it's integer or float
                if pd.api.types.is_integer_dtype(non_null_series):
                    return "NUMBER"
                else:
                    return "NUMBER(10,2)"
            
            # Check if it's datetime
            elif pd.api.types.is_datetime64_any_dtype(non_null_series):
                return "DATE"
            
            # For string/object types, determine length
            else:
                # Get max length of string values
                max_length = 0
                for value in non_null_series:
                    if value is not None:
                        str_length = len(str(value))
                        if str_length > max_length:
                            max_length = str_length
                
                # Set appropriate VARCHAR2 size
                if max_length <= 10:
                    return "VARCHAR2(10)"
                elif max_length <= 50:
                    return "VARCHAR2(50)"
                elif max_length <= 100:
                    return "VARCHAR2(100)"
                elif max_length <= 255:
                    return "VARCHAR2(255)"
                else:
                    return "VARCHAR2(500)"
                    
        except Exception as e:
            print(f"⚠️ Error inferring type for column: {str(e)}")
            return "VARCHAR2(100)"

    def process_uploaded_files(self, file_paths: list) -> Dict[str, Any]:
        """Process uploaded files and return schema information"""
        schemas = {}
        
        try:
            import pandas as pd
            import os
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    continue
                
                # Get table name from file
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                table_name = file_name.upper().replace(' ', '_').replace('-', '_')
                
                try:
                    # Read file
                    if file_path.lower().endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(file_path, sheet_name=0, nrows=10)
                    elif file_path.lower().endswith('.csv'):
                        df = pd.read_csv(file_path, nrows=10)
                    else:
                        continue
                    
                    if df.empty:
                        continue
                    
                    # Generate column definitions
                    columns = []
                    for column_name in df.columns:
                        clean_col_name = str(column_name).upper().replace(' ', '_').replace('-', '_')
                        col_type = self._infer_column_type(df[column_name])
                        col_desc = str(column_name).replace('_', ' ').title()
                        
                        columns.append({
                            "name": clean_col_name,
                            "type": col_type,
                            "description": col_desc
                        })
                    
                    schemas[table_name] = {
                        "name": table_name,
                        "columns": columns,
                        "description": f"Target table from file: {file_name}"
                    }
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
                    continue
            
            return schemas
            
        except ImportError:
            print("❌ pandas library is required for file processing. Install with: pip install pandas openpyxl")
            return {}
        except Exception as e:
            print(f"❌ Error processing files: {str(e)}")
            return {}

    def _parse_target_tables_from_text(self, target_tables_text: str) -> Dict[str, Any]:
        """Parse target table schemas from user input text"""
        import re
        
        schemas = {}
        
        try:
            # Split by table definitions (look for patterns like "TABLE_NAME:" or "TABLE_NAME\n")
            # Handle both "TABLE_NAME:" and "TABLE_NAME" followed by columns
            lines = [line.strip() for line in target_tables_text.strip().split('\n') if line.strip()]
            
            if not lines:
                return schemas
            
            current_table = None
            columns = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('--'):
                    continue
                
                # Check if this line is a table name (no comma, appears to be a table identifier)
                # Table names typically don't contain commas and are often in uppercase
                if (',' not in line and 
                    (line.isupper() or line.replace('_', '').replace(' ', '').isalnum()) and
                    not any(sql_type in line.upper() for sql_type in ['VARCHAR', 'NUMBER', 'DATE', 'CHAR'])):
                    
                    # Save previous table if exists
                    if current_table and columns:
                        schemas[current_table] = {
                            "name": current_table,
                            "columns": columns,
                            "description": f"Target table: {current_table}"
                        }
                    
                    # Start new table
                    current_table = line.replace(':', '').strip().upper()
                    columns = []
                    
                elif current_table and ',' in line:
                    # Parse column definition
                    # Remove trailing comma if present
                    if line.endswith(','):
                        line = line[:-1].strip()
                        
                    # Parse column definition: COLUMN_NAME, TYPE[, Description]
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
                
                elif not current_table and ',' in line:
                    # If we encounter columns without a table name, assume first table
                    current_table = "TARGET_TABLE"
                    columns = []
                    
                    # Parse this line as a column
                    if line.endswith(','):
                        line = line[:-1].strip()
                        
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
            
            # Save the last table
            if current_table and columns:
                schemas[current_table] = {
                    "name": current_table,
                    "columns": columns,
                    "description": f"Target table: {current_table}"
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
    
    # Example 1: Using text input for target tables
    target_tables_text = """
    TEMP_TARGET_TABLE_1
    Cluster Name, VARCHAR2(100),
    REGION, VARCHAR2(100),
    DD_CODE, VARCHAR2(100),
    DD Name, VARCHAR2(100),
    SELECTED_REC_TARGET, NUMBER,
    SELECTED_REC_INCENTIVE, NUMBER,
    All_Bundle_Target, NUMBER
    """
    
    # Process SRF with text input
    result = orchestrator.process_srf(sample_srf, target_tables_text=target_tables_text)
    
    # Example 2: Using file uploads (uncomment if you have files)
    # file_paths = ["path/to/your/target_data.csv", "path/to/another/file.xlsx"]
    # result = orchestrator.process_srf(sample_srf, file_paths=file_paths)
    
    # Example 3: Generate schema text from files (for UI text area)
    # file_paths = ["path/to/your/file.csv"]
    # schema_text = orchestrator.generate_schema_from_files(file_paths)
    # print("Generated schema text:")
    # print(schema_text)
    
    # Save outputs
    orchestrator.save_output(result)
    
    print("✅ Commission SQL generation completed!")
