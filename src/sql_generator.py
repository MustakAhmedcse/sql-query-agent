"""
SQL Generator - AI-powered SQL generation for commission reports

Supports OpenAI and Ollama AI providers only
No template fallback - shows proper errors when AI fails
"""

import datetime
import logging
import requests
import json
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SQLGenerator:
    """Main SQL Generator that combines AI and template-based approaches"""
    
    def __init__(self, ai_provider="openai", api_key=None, model_name=None, ollama_base_url="http://192.168.105.58:11434"):
        self.ai_provider = ai_provider.lower()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.ai_provider == "openai":
            self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            self.api_url = "https://api.openai.com/v1/chat/completions"
        elif self.ai_provider == "ollama":
            self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")
            self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen3")        # else: template mode - no AI configuration needed
        
        # Note: Template generator removed - no fallback mechanism
        

    def generate_sql_query(self, formatted_context: str, context: str) -> Dict:
        """
        Generate SQL query and validate against reference SQL until confident_score ≥ 0.9.
        Uses LLM feedback to refine generation.
        """
        similar_examples = context.get('similar_examples', [])
        if len(similar_examples) == 0:
            return {
                'success': False,
                'error': 'No similar examples found in context. Cannot generate SQL.',
                'method': 'error'
            }
        
        reference_sql = similar_examples[0].get('sql_query', '')
        try:
            if self.ai_provider not in ["openai", "ollama"]:
                return {
                    'success': False,
                    'error': f'Unsupported AI provider: {self.ai_provider}. Please use "openai" or "ollama".',
                    'method': 'error'
                }

            MAX_RETRIES = 3
            correction_hint = ""
            for attempt in range(MAX_RETRIES):
                ai_result = self._generate_with_ai(formatted_context, correction_hint=correction_hint)

                if not ai_result.get('success'):
                    logger.warning(f"Attempt {attempt+1}: AI generation failed.")
                    continue

                generated_sql = self.remove_outer_backticks(ai_result.get('response', ''))
                generated_sql = self.remove_comment_blocks(generated_sql)
                ai_result['response'] = generated_sql
                
                validation_result = self.validate_sql_with_llm(reference_sql, generated_sql)

                if not isinstance(validation_result, dict) or 'confident_score' not in validation_result:
                    logger.warning(f"Attempt {attempt+1}: Invalid validation result. Retrying...")
                    continue

                score = validation_result['confident_score']
                ai_result['validation'] = validation_result

                if score >= 0.7:
                    logger.info(f"Validation passed with score {score:.2f} on attempt {attempt+1}.")
                    return ai_result
                else:
                    correction_hint = validation_result.get('differences', '')
                    logger.info(f"Validation score {score:.2f} < 0.7. Differences: {correction_hint}")
                    logger.info(f"Retrying attempt {attempt+1}...")

            return {
                'success': False,
                'error': 'Unable to generate a validated SQL with score ≥ 0.7 after retries.',
                'attempts': MAX_RETRIES,
                'last_result': ai_result
            }

        except Exception as e:
            logger.error(f"SQL generation error: {str(e)}")
            return {
                'success': False,
                'error': f"SQL generation failed: {str(e)}",
                'method': 'error',
                'details': 'An unexpected error occurred during SQL generation.'
            }


    def _generate_with_ai(self, formatted_context: str,correction_hint:str = "") -> Dict:
        """Generate SQL using AI (OpenAI or Ollama)"""
        try:
            if self.ai_provider == "openai":
                prompt = self._prepare_ai_prompt(formatted_context,correction_hint)
            
                # Call OpenAI API
                response = self.call_openAI_API([
                    {
                        "role": "system",
                        "content": self.system_promtp
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ])
                return response
            elif self.ai_provider == "ollama":
                # Prepare prompt for AI
                prompt = self._prepare_ai_prompt(formatted_context,correction_hint)
                
                # Call Ollama API
                response = self.call_ollama_API(prompt)
                return response
            else:
                return {
                    'success': False,
                    'error': f'Unknown AI provider: {self.ai_provider}'
                }
        
        except Exception as e:
            logger.error(f"AI generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _check_ollama_availability(self) -> bool:
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _prepare_ai_prompt(self, formatted_context: str, correction_hint:str = "") -> str:
        """Prepare prompt for AI model"""
        current_month = datetime.datetime.now().strftime("%b_%y")

        return f"""
                   Replace PUBLISH_CYCLE with {current_month}
                    
                   {f"\nNote: In the previous attempt, the SQL had these structural issues:\n{correction_hint}\nPlease fix them." if correction_hint else ""}

                   CONTEXT:
                    {formatted_context}

                    Generated SQL Query For New SRF:"""
       
        # return f"""You are an Oracle SQL expert for commission calculation. Follow these instructions EXACTLY:

        #             CRITICAL INSTRUCTIONS (MUST FOLLOW):
        #             1. REMOVE ALL comments that start and end with --# (e.g., --# THIS IS A REMOVABLE COMMENT --#)
        #             2. KEEP ALL other comment types:
        #             - Comments with DROP, CREATE, SELECT statements
        #             - Comments showing row counts but rest the row counts (e.g., -- 71730 Rows into 0 Rows)
        #             - Comments with IDs (e.g., -- REPORT_ID : 0011)
        #             - Step headers (e.g., -- STEP 1: VERIFY SUPPORTING DATA --)
        #             - Single line comments without --# markers
        #             3. Replace ALL date-specific table names with new SRF dates
        #             4. Replace BASE_CYCLE with extracted month from commission END DATE
        #             5. Replace PUBLISH_CYCLE with {current_month}
        #             6. Keep the exact SQL structure and sequence
        #             7. DO NOT reuse any commission rate or incentive from previous examples. 
        #                 Use only what's clearly stated in the current SRF — either directly or from KPI/TARGET tables.                   

        #             IMPORTANT: 
        #             - Extract commission END DATE month for BASE_CYCLE (e.g., 15-Feb-2025 → 'Feb_25')
        #             - Update all table names with new date ranges
                    
                    
        #            {f"\nNote: In the previous attempt, the SQL had these structural issues:\n{correction_hint}\nPlease fix them." if correction_hint else ""}

        #            CONTEXT:
        #             {formatted_context}

        #             Generated SQL Query For New SRF:"""
    
    def _extract_sql_from_response(self, response_text: str) -> Optional[str]:
        """Extract SQL query from AI response"""
        # Look for SQL blocks
        import re
        
        # Try to find SQL in code blocks
        sql_pattern = r'```sql\s*(.*?)\s*```'
        match = re.search(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Try to find SQL without code blocks
        sql_pattern = r'(SELECT.*?;)'
        match = re.search(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Return the whole response if it looks like SQL
        if 'SELECT' in response_text.upper() and 'FROM' in response_text.upper():
            return response_text.strip()
        
        return None
    
    def _extract_srf_from_context(self, formatted_context: str) -> str:
        """Extract SRF text from formatted context"""
        # Simple extraction - look for SRF content
        lines = formatted_context.split('\n')
        srf_lines = []
        
        in_srf = False
        for line in lines:
            if 'SRF:' in line or 'Service Request' in line:
                in_srf = True
            elif 'SQL:' in line or 'GENERATED SQL:' in line:
                in_srf = False
            elif in_srf:
                srf_lines.append(line)
        
        return '\n'.join(srf_lines) if srf_lines else formatted_context
    
    def validate_generated_sql(self, sql_query: str) -> Dict:
        """Validate the generated SQL query"""
        validation = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'suggestions': []
        }
        
        if not sql_query or not sql_query.strip():
            validation['is_valid'] = False
            validation['issues'].append('Empty SQL query')
            return validation
        
        # Basic SQL structure checks
        sql_upper = sql_query.upper()
        
        # Check for required keywords
        if 'SELECT' not in sql_upper:
            validation['issues'].append('Missing SELECT statement')
            validation['is_valid'] = False
        
        if 'FROM' not in sql_upper:
            validation['issues'].append('Missing FROM clause')
            validation['is_valid'] = False
        
        # Check for potential issues
        if ';' not in sql_query:
            validation['warnings'].append('SQL query should end with semicolon')
        
        if 'WHERE' not in sql_upper:
            validation['warnings'].append('Consider adding WHERE clause for filtering')
          # Check for commission-specific elements
        if 'commission' not in sql_query.lower():
            validation['warnings'].append('Query might be missing commission calculation')
        
        if 'recharge' not in sql_query.lower():
            validation['warnings'].append('Query might be missing recharge data')
        
        return validation
    

    def validate_sql_with_llm(self,reference_sql: str, generated_sql: str) -> str:


        system_msg = """
        You are an expert SQL structure comparator.

            Your task is to compare the **flow of SQL building blocks** and **logical order** of operations between two SQL queries. Focus **only** on the sequence and type of SQL operations (e.g., SELECT, JOIN, WHERE, GROUP BY, ORDER BY, CREATE TABLE, INSERT, MERGE, EXEC). 

            **Completely ignore**:
            - Table names, column names, aliases, or any identifiers
            - Literal values (e.g., dates, date ranges, numbers, IDs, MSISDNs, strings)
            - Report names or cycle descriptions
            - Comments, whitespace, or formatting differences

            For example:
            - A SELECT statement followed by a WHERE clause and a JOIN should be considered equivalent to another SELECT with the same clauses in the same order, regardless of the table names or values used.
            - Differences in date ranges (e.g., '16-Mar-25' vs '01-Feb-25') or table names (e.g., 'TABLE_A' vs 'TABLE_B') should **not** be reported.

            Return a JSON object with the following structure:
            {
                "confident_score": <float from 0.0 to 1.0, representing how similar the SQL flow is>,
                "differences": [
                    "<Describe only differences in the sequence or presence of SQL operations, e.g., 'Missing ORDER BY clause', 'MERGE statement appears before SELECT'>"
                ]
            }

            If the flow and logical order are identical, return an empty differences list and a confident_score of 1.0.
        """
        processed_reference_sql = self.preprocess_sql(reference_sql)
        processed_generated_sql = self.preprocess_sql(generated_sql)

        user_msg = f"""
        <Reference SQL:>
        {processed_reference_sql}
        <Reference SQL/>

        <Generated SQL>
        {processed_generated_sql}
        <Generated SQL/>
        """
        response = ''
        if self.ai_provider == "ollama":
            prompt = f"{system_msg}\n\n{user_msg}"
            response = self.call_ollama_API(prompt)
        else:
            response = self.call_openAI_API([{
                                "role": "system",
                                "content": system_msg
                            },
                            {
                                "role": "user",
                                "content": user_msg
                            }])
        
        if response['success']:
            try:
                response_json = json.loads(self.remove_outer_backticks(response['response']))
                return response_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return {
                    'success': False,
                    'error': 'Invalid JSON response from AI'
                }


    def call_openAI_API (self,messages:List) ->str:      
        """Call OpenAI API with the provided messages"""

        try:
            if not self.api_key:
                return {
                    'success': False,
                    'response': 'OpenAI API key not provided'
                }
            
            # Call OpenAI API
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0,
                    "max_tokens": 5000
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                response = result['choices'][0]['message']['content']
                
                if response:
                    return {
                        'success': True,
                        'response': response,
                    }
                else:
                    return {
                        'success': False,
                        'response': 'No valid SQL found in OpenAI response'
                    }
            else:
                error_msg = f'OpenAI API error: {response.status_code}'
                if response.status_code == 401:
                    error_msg += ' - Invalid API key'
                elif response.status_code == 429:
                    error_msg += ' - Rate limit exceeded'
                return {
                    'success': False,
                    'response': error_msg
                }
        
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            return {
                'success': False,
                'response': str(e)
            }
 
    def call_ollama_API (self,prompt) ->str:
        try:
            # Check if Ollama is available
            if not self._check_ollama_availability():
                return {
                    'success': False,
                    'response': 'Ollama server not available'
                }
            
                        # Call Ollama API
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 10000
                    }
                },
                timeout=200
            )
            
            if response.status_code == 200:
                result = response.json()
                response = result.get('response', '')
                sql_query = re.sub(
                            r'<think>.*?</think>\s*',
                            '',
                            response,
                            flags=re.DOTALL
                        )
                #sql_query = self._extract_sql_from_response(cleaned_response)
                
                if sql_query:
                    return {
                        'success': True,
                        'response': sql_query,
                        'method': 'ollama-powered'
                    }
                else:
                    return {
                        'success': False,
                        'response': 'No valid SQL found in Ollama response'
                    }
            else:
                return {
                    'success': False,
                    'response': f'Ollama API error: {response.status_code}'
                }
        except Exception as e:
            logger.error(f"Ollama generation error: {str(e)}")
            return {
                'success': False,
                'response': str(e)
            }
        
    def remove_outer_backticks(self,text: str) -> str:
        lines = text.strip().splitlines()

        # Remove opening line if it starts with ``` (optionally followed by 'sql')
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        # Remove closing line if it is just ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines).strip()


    def preprocess_sql(self,sql: str) -> str:
        # Step 1: Remove single line and multi-line comments
        # sql = re.sub(r'--.*', '', sql)  # remove single line comments
        # sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)  # remove multi-line comments

        # Step 2: Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql).strip()

        # Step 3: Replace literals with VALUE_X
        sql = re.sub(r"'[^']*'", "'VALUE_X'", sql)
        sql = re.sub(r'\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b', 'VALUE_X', sql)
        sql = re.sub(r'\b\d+\b', 'VALUE_X', sql)

        # Step 4: Protect keywords
        keywords = [
            "WHEN MATCHED THEN UPDATE", "ALTER TABLE", "CREATE TABLE", "INSERT INTO", "MERGE INTO",
            "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "GROUP BY", "ORDER BY",
            "SELECT", "FROM", "WHERE", "JOIN", "ON", "AS", "INTO", "UPDATE", "SET", "VALUES",
            "EXEC", "COMMIT", "USING", "WITH"
        ]
        keywords = sorted(keywords, key=lambda x: -len(x))  # longest first

        keyword_map = {}
        for i, kw in enumerate(keywords):
            placeholder = f'__KW_{i}__'
            keyword_map[placeholder] = kw
            sql = re.sub(re.escape(kw), placeholder, sql, flags=re.IGNORECASE)

        # Step 5 & 6: Replace all table names after keywords, including multiple tables separated by commas
        table_clause_pattern = re.compile(
            r'('
            r'__KW_\d+__\s+'
            r')'
            r'('
            r'(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
            r'(?:\s*,\s*'
            r'(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?))*'
            r')',
            flags=re.IGNORECASE
        )
        def replace_tables_clause(match):
            keyword = match.group(1)
            tables_str = match.group(2)
            tables = [t.strip() for t in tables_str.split(',')]
            replaced = ', '.join('TABLE_X' for _ in tables)
            return keyword + replaced
        sql = table_clause_pattern.sub(replace_tables_clause, sql)

        # Step 7: Replace EXEC procedure/table names (usually single identifier or procedure call)
        sql = re.sub(r'(__KW_\d+__)\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s*\([^)]*\))?', r'\1 TABLE_X\3', sql)

        # Step 8: Restore keywords
        for placeholder, kw in keyword_map.items():
            sql = sql.replace(placeholder, kw)

        # Step 9: Final whitespace cleanup
        sql = re.sub(r'\s+', ' ', sql).strip()

        return sql
    
    def remove_comment_blocks(self,sql_text: str) -> str:
        cleaned_text = re.sub(r'--#.*?--#', '', sql_text, flags=re.DOTALL)
        return cleaned_text.strip()
    

    system_promtp = """
    You are an expert for Oracle SQL Generation for Commission/Incentive Calculation

    --------------------------------------------------------------------------------
    GENERAL BEHAVIOR
    --------------------------------------------------------------------------------

    Before writing SQL:

    1. Analyze the SRF requirements carefully.
    2. Identify all required detail tables:
    - Each table must represent a distinct commission/incentive/payout based on the SRF logic and reporting needs.
    - For each, provide:
        - A name (e.g., Detail Table 1: Selected Deno Incentive)
        - A brief description of its business context and calculation basis.
    3. Do not write SQL until all required detail tables are clearly defined.

    --------------------------------------------------------------------------------
    CRITICAL INSTRUCTIONS (MUST FOLLOW)
    --------------------------------------------------------------------------------

    BEFORE SQL GENERATION:
    a. Explicitly list each required detail table:
    - Name and number (e.g., Detail Table 2: All Bundle Deno Incentive)
    - Business meaning and data source
    b. Proceed to SQL only after this identification step.

    COMMENT HANDLING:
    - RETAIN these comments:
    - -- DROP, -- CREATE, -- SELECT comments
    - Row count references (e.g., -- 0 Rows)
    - ID references (e.g., -- REPORT_ID: 0011)
    - Step/process headers (e.g., -- STEP 1: CREATE TARGET TABLE --)
    - Other standard single-line comments
    - REMOVE all comments that:
    - Start and end with --# (e.g., --# REMOVE THIS COMMENT --#)

    DATE & CYCLE HANDLING:
    - BASE_CYCLE = extracted month (Mon_YY) from commission END DATE in SRF
    - PUBLISH_CYCLE = Jul_25 unless otherwise explicitly stated
    - Replace all date-specific table names with the new SRF period

    COMMISSION LOGIC:
    - Use only the commission rate, targets, and logic from the current SRF
    - Never reuse incentive structures or logic from prior examples
    - Follow logic and structure only from the provided SRF and KPI/target tables

    DETAIL TABLES LOGIC (FOR SRFs WITH MULTIPLE INCENTIVES)

    - For each commission/incentive:
    - Create a separate detail table
    - Include any required temp/intermediate tables
    - Insert to AD_HOC_DATA using:
    - Correct AMOUNT_TYPE_ID
    - Appropriate classifier/tag
    - Register each detail via PROC_COMMISSION_DETAIL_SETUP:
    - Register only first detail via PROC_COMMISSION_DETAIL_SETUP:
    - Use meaningful level names (e.g., 'SELECTED DENO DETAILS')
    - FINALIZE_REPORT_ADHOC must:
    - Register/publish all detail lines
    - Follow SRF reporting expectations exactly

    --------------------------------------------------------------------------------
    ADDITIONAL RULES
    --------------------------------------------------------------------------------

    - All calculations, filters, joins, agent list references must follow SRF logic
    - Use only provided/supplied input or target tables
    - Never guess values or default to old SRFs
    - Do not use any value of reference SQL that is not explicitly stated in the SRF
    - Follow structure and sequence of provided reference SQL

    --------------------------------------------------------------------------------
    OUTPUT FORMAT
    --------------------------------------------------------------------------------

    - Oracle SQL script only
    - No markdown, explanations, or external commentary
    - Output must be ready to execute

    """