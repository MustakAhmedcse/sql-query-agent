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
        
    def generate_sql_query(self, formatted_context: str) -> Dict:
        """
        Generate SQL query based on configured AI provider
        """
        try:
            # Only support AI providers - no template fallback
            if self.ai_provider not in ["openai", "ollama"]:
                return {
                    'success': False,
                    'error': f'Unsupported AI provider: {self.ai_provider}. Please use "openai" or "ollama".',
                    'method': 'error'
                }
            
            # Generate using AI providers only
            ai_result = self._generate_with_ai(formatted_context)
            
            if ai_result['success']:
                # Validate AI result
                validation = self.validate_generated_sql(ai_result['sql_query'])
                ai_result['validation'] = validation
                return ai_result
            else:
                # Return the AI error directly - no fallback
                logger.error(f"AI generation failed: {ai_result.get('error')}")
                return {
                    'success': False,
                    'error': f"AI SQL generation failed: {ai_result.get('error', 'Unknown error')}",
                    'method': ai_result.get('method', 'unknown'),
                    'details': 'Please check your AI provider configuration and try again.'
                }
        
        except Exception as e:
            logger.error(f"SQL generation error: {str(e)}")
            return {
                'success': False,
                'error': f"SQL generation failed: {str(e)}",
                'method': 'error',
                'details': 'An unexpected error occurred during SQL generation.'
            }
    
    def _generate_with_ai(self, formatted_context: str) -> Dict:
        """Generate SQL using AI (OpenAI or Ollama)"""
        try:
            if self.ai_provider == "openai":
                return self._generate_with_openai(formatted_context)
            elif self.ai_provider == "ollama":
                return self._generate_with_ollama(formatted_context)
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
    
    def _generate_with_openai(self, formatted_context: str) -> Dict:
        """Generate SQL using OpenAI"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'OpenAI API key not provided'
                }
            
            # Prepare prompt for OpenAI
            prompt = self._prepare_ai_prompt(formatted_context)
            
            # Call OpenAI API
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an Oracle SQL expert specializing in commission calculation systems. You must generate clean, executable SQL queries that follow the exact structure and logic of the provided reference example. Remove all descriptive comments except structural ones."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 3000
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                sql_query = result['choices'][0]['message']['content']
                #sql_query = self._extract_sql_from_response(cleaned)
                
                if sql_query:
                    return {
                        'success': True,
                        'sql_query': sql_query,
                        'method': 'openai-powered'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No valid SQL found in OpenAI response'
                    }
            else:
                error_msg = f'OpenAI API error: {response.status_code}'
                if response.status_code == 401:
                    error_msg += ' - Invalid API key'
                elif response.status_code == 429:
                    error_msg += ' - Rate limit exceeded'
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_with_ollama(self, formatted_context: str) -> Dict:
        """Generate SQL using Ollama"""
        try:
            # Check if Ollama is available
            if not self._check_ollama_availability():
                return {
                    'success': False,
                    'error': 'Ollama server not available'
                }
            
            # Prepare prompt for AI
            prompt = self._prepare_ai_prompt(formatted_context)
            
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
                        'sql_query': sql_query,
                        'method': 'ollama-powered'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No valid SQL found in Ollama response'
                    }
            else:
                return {
                    'success': False,
                    'error': f'Ollama API error: {response.status_code}'
                }
        
        except Exception as e:
            logger.error(f"Ollama generation error: {str(e)}")
            return {                'success': False,
                'error': str(e)
            }
    
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _prepare_ai_prompt(self, formatted_context: str) -> str:
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