from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser
from models import CommissionState, SQLStep, TableSchema
from typing import Dict, Any, List
import json
import re
from datetime import datetime

class MetadataExtractor:
    """Extracts basic metadata from SRF text for reporting purposes"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = PromptTemplate(
            input_variables=["srf_text"],
            template="""
            Extract basic metadata from this commission calculation SRF for reporting purposes.
            
            SRF Text:
            {srf_text}
            
            Extract and return ONLY a JSON object with these fields (use "Not specified" if not found):
            - commission_name: The campaign name
            - start_date: Start date (YYYY-MM-DD format)
            - end_date: End date (YYYY-MM-DD format) 
            - receiver_channel: Who receives commission (Distributor/Retailer/etc.)
            - kpi_type: Type of KPI mentioned
            - has_detail_tables: true/false - whether SRF contains explicit detail table specifications
            
            For has_detail_tables, look for keywords like: "detail format", "detail table", "output table", 
            "expected output", "detail level", "detail 1", "detail 2", "summary detail", "transaction detail",
            "create table", "output format", AND check if actual table structure/column specifications are provided.
            Only return true if BOTH detail table keywords AND structure specifications are found.
            
            Return ONLY valid JSON format with no additional text.
            """
        )
    
    def extract(self, state: CommissionState) -> CommissionState:
        """Extract basic metadata from SRF text"""
        try:
            response = self.llm.invoke(
                self.prompt.format(srf_text=state["srf_text"])
            )
            
            # Parse JSON response
            metadata_text = response.content.strip()
            if metadata_text.startswith("```json"):
                metadata_text = metadata_text[7:-3].strip()
            elif metadata_text.startswith("```"):
                metadata_text = metadata_text[3:-3].strip()
            
            metadata = json.loads(metadata_text)
            
            # Validate and clean metadata
            metadata = self._validate_metadata(metadata)
            
            state["metadata"] = metadata
            
        except Exception as e:
            state["errors"].append(f"Metadata extraction failed: {str(e)}")
            # Provide minimal default metadata
            state["metadata"] = self._get_default_metadata()
        
        return state
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted metadata"""
        # Ensure required fields exist
        required_fields = ["commission_name", "start_date", "end_date", "receiver_channel", "kpi_type", "has_detail_tables"]
        
        for field in required_fields:
            if field not in metadata:
                if field == "has_detail_tables":
                    metadata[field] = False
                else:
                    metadata[field] = "Not specified"
        
        # Ensure has_detail_tables is boolean
        if isinstance(metadata.get("has_detail_tables"), str):
            metadata["has_detail_tables"] = metadata["has_detail_tables"].lower() in ["true", "yes", "1"]
        elif not isinstance(metadata.get("has_detail_tables"), bool):
            metadata["has_detail_tables"] = False
        
        # Validate date formats
        for date_field in ["start_date", "end_date"]:
            if date_field in metadata:
                try:
                    datetime.strptime(metadata[date_field], "%Y-%m-%d")
                except:
                    metadata[date_field] = "2024-01-01"  # Default
        
        return metadata
    
    def _get_default_metadata(self) -> Dict[str, Any]:
        """Provide minimal default metadata structure"""
        return {
            "commission_name": "Commission Campaign",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "receiver_channel": "Distributor",
            "kpi_type": "Recharge",
            "has_detail_tables": False
        }

class SQLStepGenerator:
    """Generates individual SQL steps for commission calculation"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.step_templates = {
            "setup": self._get_setup_template(),
            "mapping": self._get_mapping_template(),
            "calculation": self._get_calculation_template(),
            "detail_tables": self._get_detail_tables_template(),
            "report_setup": self._get_report_setup_template()
        }
    
    def generate_all_steps(self, state: CommissionState) -> CommissionState:
        """Generate all SQL steps for commission calculation"""
        try:
            steps = []
            srf_text = state["srf_text"]
            schemas = state["table_schemas"]
            previous_queries = []  # Store previous step queries
            
            # Step 1: Setup and data cleaning
            step1 = self._generate_setup_step(srf_text, schemas, previous_queries)
            steps.append(step1)
            previous_queries.append(step1.sql_query)
            
            # Step 2: Create mapping table
            step2 = self._generate_mapping_step(srf_text, schemas, previous_queries)
            steps.append(step2)
            previous_queries.append(step2.sql_query)
            
            # Step 3: Calculation logic (can be multiple sub-steps)
            calculation_steps = self._generate_calculation_steps(srf_text, schemas, previous_queries)
            steps.extend(calculation_steps)
            for calc_step in calculation_steps:
                previous_queries.append(calc_step.sql_query)
            
            # Step 4: Insert into detail tables (if specified in metadata)
            detail_steps = self._generate_detail_table_steps(srf_text, schemas, previous_queries, state.get("metadata", {}))
            if detail_steps:
                steps.extend(detail_steps)
                for detail_step in detail_steps:
                    previous_queries.append(detail_step.sql_query)
            
            # Step 5: Report setup and publishing (always generate this step)
            report_setup_steps = self._generate_report_setup_steps(srf_text, schemas, previous_queries, state.get("metadata", {}))
            steps.extend(report_setup_steps)
            for report_step in report_setup_steps:
                previous_queries.append(report_step.sql_query)
            
            # Update step numbers sequentially
            for i, step in enumerate(steps, 1):
                step.step_number = i
                # Update dependencies to reflect correct step numbers
                if i > 1:
                    step.depends_on = [i-1]
            
            state["sql_steps"] = steps
            
        except Exception as e:
            state["errors"].append(f"SQL step generation failed: {str(e)}")
        
        return state
    
    def _generate_setup_step(self, srf_text: str, schemas: Dict, previous_queries: List[str]) -> SQLStep:
        """Generate setup and data cleaning step"""
        permanent_schemas = self._format_permanent_schemas_for_prompt(schemas)
        target_tables = self._format_target_tables_for_prompt(schemas)
        previous_context = self._format_previous_queries_for_prompt(previous_queries)
        
        prompt = self.step_templates["setup"].format(
            srf_text=srf_text,
            available_schemas=permanent_schemas,
            target_tables=target_tables,
            previous_queries=previous_context
        )
        
        response = self.llm.invoke(prompt)
        
        return SQLStep(
            step_number=1,
            name="setup_and_cleaning",
            description="Setup and data cleaning operations, especially DD_CODE cleaning before joins",
            sql_query=self._extract_sql_from_response(response.content),
            depends_on=[],
            validation_query="-- Validate setup: Check if target tables are accessible and DD_CODE is cleaned"
        )
    
    def _generate_mapping_step(self, srf_text: str, schemas: Dict, previous_queries: List[str]) -> SQLStep:
        """Generate mapping table creation step"""
        permanent_schemas = self._format_permanent_schemas_for_prompt(schemas)
        target_tables = self._format_target_tables_for_prompt(schemas)
        previous_context = self._format_previous_queries_for_prompt(previous_queries)
        
        prompt = self.step_templates["mapping"].format(
            srf_text=srf_text,
            available_schemas=permanent_schemas,
            target_tables=target_tables,
            previous_queries=previous_context
        )
        
        response = self.llm.invoke(prompt)
        
        return SQLStep(
            step_number=2,
            name="create_mapping",
            description="Create mapping table between target and retailer MSISDN using agent list",
            sql_query=self._extract_sql_from_response(response.content),
            depends_on=[1],
            validation_query="-- Validate mapping: Check mapping table record count and join quality"
        )
    
    def _generate_calculation_steps(self, srf_text: str, schemas: Dict, previous_queries: List[str]) -> List[SQLStep]:
        """Generate calculation logic steps (can be multiple based on SRF complexity)"""
        permanent_schemas = self._format_permanent_schemas_for_prompt(schemas)
        target_tables = self._format_target_tables_for_prompt(schemas)
        previous_context = self._format_previous_queries_for_prompt(previous_queries)
        
        prompt = self.step_templates["calculation"].format(
            srf_text=srf_text,
            available_schemas=permanent_schemas,
            target_tables=target_tables,
            previous_queries=previous_context
        )
        
        response = self.llm.invoke(prompt)
        
        # For now, return single calculation step, but this could be enhanced
        # to split complex calculations into multiple steps
        return [SQLStep(
            step_number=3,
            name="calculation_logic",
            description="Main commission calculation logic according to SRF requirements",
            sql_query=self._extract_sql_from_response(response.content),
            depends_on=[2],
            validation_query="-- Validate calculations: Check commission amounts and achievement percentages"
        )]
    
    def _generate_detail_table_steps(self, srf_text: str, schemas: Dict, previous_queries: List[str], metadata: Dict) -> List[SQLStep]:
        """Generate detail table creation steps if specified in metadata"""
        # Check metadata for detail table requirement
        has_detail_tables = metadata.get("has_detail_tables", False)
        
        if not has_detail_tables:
            return []
        
        permanent_schemas = self._format_permanent_schemas_for_prompt(schemas)
        target_tables = self._format_target_tables_for_prompt(schemas)
        previous_context = self._format_previous_queries_for_prompt(previous_queries)
        
        prompt = self.step_templates["detail_tables"].format(
            srf_text=srf_text,
            available_schemas=permanent_schemas,
            target_tables=target_tables,
            previous_queries=previous_context
        )
        
        response = self.llm.invoke(prompt)
        
        return [SQLStep(
            step_number=4,
            name="create_detail_tables",
            description="Create and populate detail tables as specified in SRF",
            sql_query=self._extract_sql_from_response(response.content),
            depends_on=[3],
            validation_query="-- Validate detail tables: Check record counts and data completeness"
        )]
    
    def _generate_report_setup_steps(self, srf_text: str, schemas: Dict, previous_queries: List[str], metadata: Dict = None) -> List[SQLStep]:
        """Generate report setup and publishing steps"""
        permanent_schemas = self._format_permanent_schemas_for_prompt(schemas)
        target_tables = self._format_target_tables_for_prompt(schemas)
        previous_context = self._format_previous_queries_for_prompt(previous_queries)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Use metadata to determine if detail tables exist, fallback to previous query analysis
        if metadata:
            has_detail_tables = metadata.get("has_detail_tables", False)
        else:
            has_detail_tables = self._has_detail_tables_in_previous_queries(previous_queries)
        
        prompt = self.step_templates["report_setup"].format(
            srf_text=srf_text,
            available_schemas=permanent_schemas,
            target_tables=target_tables,
            previous_queries=previous_context,
            current_date=current_date,
            has_detail_tables=has_detail_tables
        )
        
        response = self.llm.invoke(prompt)
        
        return [SQLStep(
            step_number=5,
            name="report_setup_and_publish",
            description="Setup commission report in platform and prepare for publishing",
            sql_query=self._extract_sql_from_response(response.content),
            depends_on=[4] if previous_queries else [3],  # Depends on previous step
            validation_query="-- Validate report setup: Check report IDs, cycle IDs, and commission amounts"
        )]
    
    def _format_previous_queries_for_prompt(self, previous_queries: List[str]) -> str:
        """Format previous step queries for inclusion in prompts"""
        if not previous_queries:
            return "No previous queries (this is the first step)."
        
        context = "Previous step queries (for reference and table/CTE reuse):\n\n"
        for i, query in enumerate(previous_queries, 1):
            context += f"=== STEP {i} QUERY ===\n"
            context += f"{query}\n\n"
        
        context += "IMPORTANT: You can reference any temp tables, CTEs, or result sets created in the above queries.\n"
        context += "Do NOT recreate existing tables/CTEs. Build upon what's already been created.\n"
        context += "CRITICAL: If previous steps have already filtered data, use that filtered data directly - do NOT re-apply the same filters.\n"
        context += "The data from previous steps is already clean and filtered according to SRF requirements.\n\n"
        
        return context
    
    def _has_detail_tables_in_previous_queries(self, previous_queries: List[str]) -> bool:
        """Check if detail tables were created in previous queries"""
        if not previous_queries:
            return False
        
        # Look for common detail table patterns in previous queries
        detail_table_patterns = [
            'TEMP_FOR_D1',
            'TEMP_FOR_D2', 
            'TEMP_FOR_DETAIL',
            'CREATE TABLE TEMP_',
            'CREATE OR REPLACE TABLE TEMP_',
            'INSERT INTO TEMP_FOR_',
            'detail.*table',
            'summary.*table',
            'transaction.*table'
        ]
        
        all_queries = ' '.join(previous_queries).upper()
        
        for pattern in detail_table_patterns:
            if pattern.upper().replace('.*', '') in all_queries:
                return True
                
        return False
    
    def _format_schemas_for_prompt(self, schemas: Dict) -> str:
        """Format table schemas for inclusion in prompts"""
        schema_text = "Available table schemas:\n\n"
        
        for table_name, schema in schemas.items():
            schema_text += f"Table: {table_name}\n"
            schema_text += f"Description: {schema.get('description', 'No description')}\n"
            schema_text += "Columns:\n"
            
            for col in schema.get('columns', []):
                schema_text += f"  - {col['name']} ({col['type']}): {col['description']}\n"
            
            schema_text += "\n"
        
        return schema_text
    
    def _format_target_tables_for_prompt(self, schemas: Dict) -> str:
        """Format target table schemas separately for inclusion in prompts"""
        target_schema_text = "Target table schemas (provided by user with data):\n\n"
        
        # Filter for target tables (these are typically the ones uploaded or provided by user)
        target_tables = {k: v for k, v in schemas.items() if self._is_target_table(k, v)}
        
        if not target_tables:
            target_schema_text += "No target tables provided.\n\n"
            return target_schema_text
        
        for table_name, schema in target_tables.items():
            target_schema_text += f"Table: {table_name}\n"
            target_schema_text += f"Description: {schema.get('description', 'User-provided target table with data')}\n"
            target_schema_text += "Columns:\n"
            
            for col in schema.get('columns', []):
                target_schema_text += f"  - {col['name']} ({col['type']}): {col['description']}\n"
            
            target_schema_text += "\n"
        
        return target_schema_text
    
    def _is_target_table(self, table_name: str, schema: Dict) -> bool:
        """Determine if a table is a target table (user-provided) vs permanent table"""
        # Target tables are typically those that don't have standard permanent table patterns
        permanent_patterns = [
            'AGENT_LIST_DAILY', 'COMMISSIONREPORT', 'COMMISSIONCYCLE', 
            'COMMISSIONCYCLEREPORTS', 'AD_HOC_DATA', 'TOPUP_TRANSACTION',
            'RECHARGE_TRANSACTION', 'BALANCE_TRANSACTION'
        ]
        
        # Check if table name matches permanent table patterns
        table_upper = table_name.upper()
        for pattern in permanent_patterns:
            if pattern in table_upper:
                return False
        
        # Also check description for hints
        description = schema.get('description', '').lower()
        if any(keyword in description for keyword in ['permanent', 'system', 'platform', 'daily']):
            return False
        
        return True
    
    def _format_permanent_schemas_for_prompt(self, schemas: Dict) -> str:
        """Format only permanent table schemas for inclusion in prompts"""
        schema_text = "Available permanent table schemas:\n\n"
        
        # Filter for permanent tables only
        permanent_tables = {k: v for k, v in schemas.items() if not self._is_target_table(k, v)}
        
        for table_name, schema in permanent_tables.items():
            schema_text += f"Table: {table_name}\n"
            schema_text += f"Description: {schema.get('description', 'No description')}\n"
            schema_text += "Columns:\n"
            
            for col in schema.get('columns', []):
                schema_text += f"  - {col['name']} ({col['type']}): {col['description']}\n"
            
            schema_text += "\n"
    
    def _extract_sql_from_response(self, response_content: str) -> str:
        """Extract SQL code from LLM response"""
        # Remove markdown code blocks if present
        content = response_content.strip()
        
        # Look for SQL code blocks
        sql_pattern = r'```sql\s*(.*?)\s*```'
        matches = re.findall(sql_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, look for SQL keywords and return relevant content
        if any(keyword in content.upper() for keyword in ['SELECT', 'CREATE', 'INSERT', 'UPDATE', 'WITH']):
            return content.strip()
        
        return "-- No SQL found in response\n" + content
    
    def _get_setup_template(self) -> PromptTemplate:
        return PromptTemplate(
            input_variables=["srf_text", "available_schemas", "target_tables", "previous_queries"],
            template="""
            You are a Oracle SQL expert generating setup queries for commission calculation.

            SRF Requirements:
            {srf_text}

            Available Permanent Tables (for reference and joins):
            {available_schemas}

            Target Tables:
            {target_tables}

            Previous Step Queries:
            {previous_queries}

            Requirements:
            1. Reference target tables directly (pre-filtered data, no WHERE clauses needed)
            2. Setup join columns (DD_CODE, etc.) for mapping with permanent tables
            3. Create temporary structures if needed for subsequent processing
            4. Multiple target tables serve different purposes - reference separately

            CRITICAL: Target tables contain only relevant data - use ALL rows without filtering.
            Only filter permanent tables if needed for date ranges or joins.

            Return executable Oracle SQL with comments.
            """
        )
    
    def _get_mapping_template(self) -> PromptTemplate:
        return PromptTemplate(
            input_variables=["srf_text", "available_schemas", "target_tables", "previous_queries"],
            template="""
            You are a Oracle SQL expert generating mapping queries for commission calculation.
            
            SRF Requirements:
            {srf_text}
            
            Available Permanent Tables (for reference and joins):
            {available_schemas}

            Target Tables:
            {target_tables}
            
            Previous Step Queries:
            {previous_queries}
            
            Generate SQL for MAPPING step that:
            1. Creates mapping table between target table and retailer MSISDN
            2. Uses AGENT_LIST_DAILY for the mapping date(data_date) specified in SRF
            3. Joins target DD_CODE with agent hierarchy (TOPUP_MSISDN, RETAILER_CODE, etc.)
            4. If previous steps have filtered data, use the already-filtered results - do NOT re-apply filters
            5. Includes all necessary fields for subsequent calculations
            6. References existing temp tables/CTEs from previous steps instead of recreating them
            
            Pay attention to:
            - Mapping date mentioned in the SRF
            - If previous steps applied filters, use that filtered data directly
            - Only apply new filters if explicitly required by SRF and not already applied in previous steps
            - Build upon tables already created in previous steps
            
            CRITICAL RULE: 
            - If previous queries have already filtered the data according to SRF requirements, do NOT re-filter
            - Use the filtered datasets from previous steps as your source data
            - Only add filters if they are new requirements from SRF not covered in previous steps
            
            Return only executable Oracle SQL code with comments.
            """
        )
    
    def _get_calculation_template(self) -> PromptTemplate:
        return PromptTemplate(
            input_variables=["srf_text", "available_schemas", "target_tables", "previous_queries"],
            template="""
            You are a Oracle SQL expert generating commission calculation logic.
            
            SRF Requirements:
            {srf_text}
            
            Available Permanent Tables (for reference and joins):
            {available_schemas}

            Target Tables:
            {target_tables}
            
            Previous Step Queries:
            {previous_queries}
            
            Generate SQL for CALCULATION LOGIC that:
            1. Implements the specific business logic described in the SRF
            2. Handles KPI calculations (recharge amounts, transaction counts, etc.)
            3. Applies target achievement logic with proper rounding rules
            4. Calculates commission amounts based on achievement percentages
            5. Implements any bonus or incentive logic mentioned
            6. Uses the already-filtered and mapped data from previous steps - do NOT re-filter
            7. References tables/CTEs created in previous steps instead of recreating them
            
            Pay special attention to:
            - Selected deno values mentioned in SRF
            - Mathematical rounding rules specified
            - Target achievement thresholds
            - Bonus calculation conditions
            - Commission rate applications
            
            IMPORTANT: Use the pre-filtered data from previous steps as your source.
            Do NOT re-apply filters that were already applied in setup or mapping steps.
            Focus on calculations and business logic, not data filtering.
            
            Return only executable Oracle SQL code with detailed comments explaining each calculation step.
            """
        )
    
    def _get_detail_tables_template(self) -> PromptTemplate:
        return PromptTemplate(
            input_variables=["srf_text", "available_schemas", "target_tables", "previous_queries"],
            template="""
            Generate Oracle SQL for DETAIL TABLES step of commission calculation.
            
            SRF: {srf_text}
            Permanent Tables: {available_schemas}
            Target Tables: {target_tables}
            Previous Queries: {previous_queries}
            
            Requirements:
            1. Create tables ONLY if SRF provides detailed format specifications
            2. Use exact SRF table naming (TEMP_FOR_*, etc.)
            3. Include ONLY columns explicitly listed in SRF detail specs
            4. Use calculated data from previous steps
            5. If SRF lacks detail specifications, return comment explaining no details provided
            
            CRITICAL: Only proceed if SRF contains explicit detail table format specifications.
            If no detailed format is provided, return: -- No detail table specifications provided in SRF
            
            Return executable Oracle SQL with CREATE and INSERT statements.
            """
        )
    
    def _get_report_setup_template(self) -> PromptTemplate:
        return PromptTemplate(
            input_variables=["srf_text", "available_schemas", "target_tables", "previous_queries", "current_date", "has_detail_tables"],
            template="""
            Generate Oracle SQL for REPORT SETUP AND PUBLISHING step of commission calculation.
            
            SRF: {srf_text}
            Permanent Tables: {available_schemas}
            Target Tables: {target_tables}
            Previous Queries: {previous_queries}
            Current Datetime: {current_date}
            Has Detail Tables: {has_detail_tables}
            
            Requirements:
            1. Setup commission report in platform
            2. Retrieve report IDs, cycle IDs based on commission dates
            3. Insert calculated commission data into AD_HOC_DATA table
            4. Setup commission detail tables ONLY if detail tables were created in previous steps
            5. Finalize and publish the report
            
            TEMPLATE:
            --------------------------------- REPORT SETUP QUERY -----------------------------------------
            
            -- PREPARE FOR REPORT PUBLISHING
            SELECT REPORTID REPORT_ID FROM COMMISSIONREPORT WHERE REPORTNAME = '[COMMISSION_NAME]';
            
            -- BASE_CYCLE = month of commission END DATE (Mar_25)
            SELECT CYCLEID BASE_CYCLE_ID FROM COMMISSIONCYCLE WHERE CYCLEDESCRIPTION = '[END_DATE_MONTH_YEAR]';
            
            SELECT REPORT_CYCLE_ID,* FROM COMMISSIONCYCLEREPORTS where REPORTID = [REPORT_ID] and CYCLEID = [BASE_CYCLE_ID];
            
            DELETE FROM AD_HOC_DATA WHERE REPORT_CYCLE_ID = [REPORT_CYCLE_ID];
            commit;
            
            --INSERT CHANNEL WISE CALCULATED COMMISSION DATA
            INSERT INTO AD_HOC_DATA (ID, REPORT_CYCLE_ID, CHANNEL_CODE, COMMISSION_AMOUNT)
            SELECT AD_HOC_DATA_ID.NEXTVAL ID, [REPORT_CYCLE_ID] REPORT_CYCLE_ID, [CHANNEL_CODE_COLUMN], [COMMISSION_AMOUNT_COLUMN]
            FROM [DETAIL_TABLE_NAME];
            commit;           
            
            SELECT CYCLEID PUBLISH_CYCLE_ID FROM COMMISSIONCYCLE WHERE CYCLEDESCRIPTION = '[CURRENT_MONTH_YEAR]';
            
            -- CONDITIONAL: Setup commission details ONLY if detail tables exist
            -- If Has Detail Tables = True, include PROC_COMMISSION_DETAIL_SETUP
            -- If Has Detail Tables = False, skip this step with comment
            -- PROC_COMMISSION_DETAIL_SETUP can take up to 9 detail tables
            -- Identify all detail tables created in previous steps and include them
            -- Format: PROC_COMMISSION_DETAIL_SETUP(<REPORT_TITLE>, <PUBLISH_CYCLE_ID>, <DETAIL1>, <LEVEL1>, <DETAIL2>, <LEVEL2>, ..., <DETAIL9>, <LEVEL9>)
            EXEC PROC_COMMISSION_DETAIL_SETUP('[COMMISSION_NAME]', [PUBLISH_CYCLE_ID], '[ALL_DETAIL_TABLES_AND_LEVELS]');
            
            -- FINALIZE AND PUBLISH COMMISSION REPORT
            EXEC FINALIZE_REPORT_ADHOC('[COMMISSION_NAME]','[REPORT_CYCLE_ID]', '[END_DATE_MONTH_YEAR]', '[CURRENT_MONTH_YEAR]', 290, 1);
            
            Replace placeholders with actual values from SRF/previous steps:
            - [COMMISSION_NAME]: Extract from commission name in SRF
            - [END_DATE_MONTH_YEAR]: Format end date as 'Mon_YY' (e.g., 'Mar_25' for March 2025)
            - [CURRENT_MONTH_YEAR]: Current month formatted as 'Mon_YY'
            - [CHANNEL_CODE_COLUMN]: The column containing channel/distributor codes from detail table
            - [COMMISSION_AMOUNT_COLUMN]: The column containing commission amounts from detail table
            - [DETAIL_TABLE_NAME]: Name of the detail table created in previous steps
            - [ALL_DETAIL_TABLES_AND_LEVELS]: Scan previous steps for all detail tables created (TEMP_FOR_*, etc.) 
              and format as: 'TABLE1_NAME', 'LEVEL1_DESC', 'TABLE2_NAME', 'LEVEL2_DESC', ...
              Example: 'TEMP_FOR_D1_CAMPAIGN_SUMMARY', 'Summary Details', 'TEMP_FOR_D2_CAMPAIGN_DETAIL', 'Transaction Details'
              Can include up to 9 detail table pairs (table_name, level_description)
            
            CRITICAL: Only include PROC_COMMISSION_DETAIL_SETUP if has_detail_tables=True
            If has_detail_tables=False, add comment: -- No detail tables created, skipping PROC_COMMISSION_DETAIL_SETUP
            
            
            Return only executable Oracle SQL code with proper comments and placeholder updates.
            """
        )
