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
        
    # def generate_sql_query(self, formatted_context: str) -> Dict:
    #     """
    #     Generate SQL query based on configured AI provider
    #     """
    #     try:
    #         # Only support AI providers - no template fallback
    #         if self.ai_provider not in ["openai", "ollama"]:
    #             return {
    #                 'success': False,
    #                 'error': f'Unsupported AI provider: {self.ai_provider}. Please use "openai" or "ollama".',
    #                 'method': 'error'
    #             }
            
    #         # Generate using AI providers only
    #         ai_result = self._generate_with_ai(formatted_context)
            
    #         if ai_result['success']:
    #             # Validate AI result
    #             validation = self.validate_generated_sql(ai_result['sql_query'])
    #             ai_result['validation'] = validation
    #             return ai_result
    #         else:
    #             # Return the AI error directly - no fallback
    #             logger.error(f"AI generation failed: {ai_result.get('error')}")
    #             return {
    #                 'success': False,
    #                 'error': f"AI SQL generation failed: {ai_result.get('error', 'Unknown error')}",
    #                 'method': ai_result.get('method', 'unknown'),
    #                 'details': 'Please check your AI provider configuration and try again.'
    #             }
        
    #     except Exception as e:
    #         logger.error(f"SQL generation error: {str(e)}")
    #         return {
    #             'success': False,
    #             'error': f"SQL generation failed: {str(e)}",
    #             'method': 'error',
    #             'details': 'An unexpected error occurred during SQL generation.'
    #         }
    
    def generate_sql_query(self, formatted_context: str, context: str) -> Dict:
        """
        Generate SQL query and validate against reference SQL until confident_score ≥ 0.9.
        Uses LLM feedback to refine generation.
        """
        similar_examples = context.get('similar_examples', [])[0]
        reference_sql = similar_examples.get('sql_query', '')
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

                generated_sql = ai_result.get('response', '')
                validation_result = self.validate_sql_with_llm(reference_sql, generated_sql)

                if not isinstance(validation_result, dict) or 'confident_score' not in validation_result:
                    logger.warning(f"Attempt {attempt+1}: Invalid validation result. Retrying...")
                    continue

                score = validation_result['confident_score']
                ai_result['validation'] = validation_result

                if score >= 0.9:
                    logger.info(f"Validation passed with score {score:.2f} on attempt {attempt+1}.")
                    return ai_result
                else:
                    correction_hint = validation_result.get('differences', '')
                    logger.info(f"Validation score {score:.2f} < 0.9. Differences: {correction_hint}")
                    logger.info(f"Retrying attempt {attempt+1}...")

            return {
                'success': False,
                'error': 'Unable to generate a validated SQL with score ≥ 0.9 after retries.',
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
                        "content": "You are an expert SQL generator for commission reports."
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
       
        return f"""You are an Oracle SQL expert for commission calculation. Follow these instructions EXACTLY:

                    CRITICAL INSTRUCTIONS (MUST FOLLOW):
                    1. REMOVE ALL descriptive comment lines from the generated SQL
                    2. KEEP ONLY these comment types:
                    - Comments with DROP, CREATE, SELECT statements
                    - Comments showing row counts (e.g., -- 71730 Rows)
                    - Comments with IDs (e.g., -- REPORT_ID : 0011)
                    3. Replace ALL date-specific table names with new SRF dates
                    4. Replace BASE_CYCLE with extracted month from commission END DATE
                    5. Replace PUBLISH_CYCLE with {current_month}
                    6. Keep the exact SQL structure and sequence

                    REFERENCE EXAMPLE:
                    {formatted_context}

                    TASK: Generate SQL for the NEW SRF following the exact same structure and logic.

                    IMPORTANT: 
                    - Extract commission END DATE month for BASE_CYCLE (e.g., 15-Feb-2025 → 'Feb_25')
                    - Use {current_month} for PUBLISH_CYCLE
                    - Update all table names with new date ranges
                    - Remove descriptive comments but keep structural comments
                    
                   {f"\nNote: In the previous attempt, the SQL had these structural issues:\n{correction_hint}\nPlease fix them." if correction_hint else ""}

                    Generated SQL Query:"""
    
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
                response_json = json.loads(response['response'])
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
                    "max_tokens": 3000
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