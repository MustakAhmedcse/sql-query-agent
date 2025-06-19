"""
SQL Generator - AI-powered SQL generation with fallback to template-based generation

Combines both AI and template approaches for robust SQL generation
Supports OpenAI, Ollama, and Template-only modes
"""

import logging
import requests
import json
import os
from typing import Dict, List, Optional
from template_sql_generator import TemplateBasedSQLGenerator

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
            self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen3")
        # else: template mode - no AI configuration needed
        
        # Initialize template generator for fallback
        self.template_generator = TemplateBasedSQLGenerator()
    
    def generate_sql_query(self, formatted_context: str) -> Dict:
        """
        Generate SQL query based on configured AI provider
        """
        try:
            # For template-only mode, skip AI generation
            if self.ai_provider == "template":
                logger.info("Using template-based generation (AI disabled)")
                return self._generate_with_template(formatted_context)
            
            # For AI providers (OpenAI/Ollama), try AI first, fallback to template
            ai_result = self._generate_with_ai(formatted_context)
            
            if ai_result['success']:
                # Validate AI result
                validation = self.validate_generated_sql(ai_result['sql_query'])
                ai_result['validation'] = validation
                return ai_result
            else:
                logger.warning(f"AI generation failed: {ai_result.get('error')}")
        
        except Exception as e:
            logger.warning(f"AI generation error: {str(e)}")
        
        # Fallback to template-based generation
        logger.info("Falling back to template-based generation...")
        return self._generate_with_template(formatted_context)
    
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
                            "content": "You are an expert SQL developer specializing in MyBL Commission reports for a telecom company. Generate accurate, executable SQL queries based on SRF requirements."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                sql_query = self._extract_sql_from_response(result['choices'][0]['message']['content'])
                
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
                        "num_predict": 2000
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                sql_query = self._extract_sql_from_response(result.get('response', ''))
                
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
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_with_template(self, formatted_context: str) -> Dict:
        """Generate SQL using template-based approach"""
        try:
            # Extract SRF text from context
            srf_text = self._extract_srf_from_context(formatted_context)
            
            # Use template generator
            result = self.template_generator.generate_sql_from_srf(srf_text)
            
            if result['success']:
                # Normalize the key name for consistency
                if 'generated_sql' in result:
                    result['sql_query'] = result['generated_sql']
                
                # Add validation
                validation = self.validate_generated_sql(result['sql_query'])
                result['validation'] = validation
                result['method'] = 'template-based'
            
            return result
        
        except Exception as e:
            logger.error(f"Template generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'method': 'template-based'
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
        return f"""You are an expert SQL developer specializing in MyBL Commission reports for a telecom company.
Your task is to generate accurate SQL queries based on SRF (Service Request Form) requirements.

CONTEXT:
{formatted_context}

REQUIREMENTS:
1. Generate a complete, executable SQL query
2. Use proper table names and column names for MyBL commission system
3. Include all necessary conditions from the SRF
4. Add comments explaining key parts
5. Focus on commission calculation logic
6. Handle time-based conditions if specified
7. Include proper date filtering
8. Use appropriate joins and aggregations

Generate ONLY the SQL query with comments. Do not include explanations outside the SQL.

SQL Query:"""
    
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

# Backward compatibility alias
CommissionSQLGenerator = SQLGenerator