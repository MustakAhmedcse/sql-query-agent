"""
Main Application - সব components একসাথে integrate করি
Simple interface for easy use
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import configuration
from config.settings import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommissionAIAssistant:
    """Main Commission AI Assistant class"""
    
    def __init__(self):
        self.data_processor = None
        self.embedding_manager = None
        self.rag_system = None
        self.sql_generator = None
        self.is_initialized = False
        
    def initialize_system(self, jsonl_file_path=None):
        """
        Complete system initialize করি
        """
        try:
            print("🚀 Initializing Commission AI Assistant...")
            
            # Step 1: Data Processing
            if jsonl_file_path:
                print("\n1️⃣ Processing training data...")
                from data_processor import process_your_data
                processed_data = process_your_data(jsonl_file_path)
                
                if not processed_data:
                    raise Exception("Data processing failed")
                    
                print("✅ Data processing completed!")
            else:
                print("⚠️  No training data provided, using existing processed data")
              # Step 2: Setup Embeddings (smart detection)
            print("\n2️⃣ Setting up embeddings...")
            from embedding_manager import setup_embeddings_from_processed_data
            processed_file = "./data/training_data/processed_training_data.json"
            
            if os.path.exists(processed_file):
                # Web interface এ সবসময় existing embedding skip করবে
                # নতুন ট্রেনিং ডাটা আপলোড করলে শুধু তখন force_recreate=True
                force_recreate = bool(jsonl_file_path)  # নতুন ডাটা থাকলে recreate
                self.embedding_manager = setup_embeddings_from_processed_data(processed_file, force_recreate=force_recreate)
                if not self.embedding_manager:
                    raise Exception("Embedding setup failed")
                print("✅ Embeddings setup completed!")
            else:
                raise Exception(f"Processed data file not found: {processed_file}")
              # Step 3: Initialize RAG System
            print("\n3️⃣ Initializing RAG system...")
            from rag_system import RAGSystem
            self.rag_system = RAGSystem(self.embedding_manager, confidence_threshold=settings.CONFIDENCE_THRESHOLD)
            print("✅ RAG system initialized!")
            
            # Step 4: Initialize SQL Generator
            print("\n4️⃣ Initializing SQL generator...")
            from sql_generator import SQLGenerator
              # Initialize SQL generator based on configured AI provider
            ai_provider = os.getenv("AI_PROVIDER", "openai").lower()
            
            if ai_provider == "openai":
                openai_key = os.getenv("OPENAI_API_KEY")
                openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                
                if openai_key:
                    print(f"   Using OpenAI ({openai_model}) for SQL generation...")
                    self.sql_generator = SQLGenerator(
                        ai_provider="openai",
                        api_key=openai_key,
                        model_name=openai_model
                    )
                else:
                    raise Exception("OpenAI selected but no API key found. Please set OPENAI_API_KEY in .env file.")
            elif ai_provider == "ollama":
                ollama_url = os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")
                ollama_model = os.getenv("OLLAMA_MODEL", "qwen3")
                
                print(f"   Using Ollama ({ollama_model}) for SQL generation...")
                self.sql_generator = SQLGenerator(
                    ai_provider="ollama",
                    model_name=ollama_model,
                    ollama_base_url=ollama_url
                )
            else:
                raise Exception(f"Unsupported AI provider '{ai_provider}'. Please use 'openai' or 'ollama'.")
                
            print("✅ SQL generator initialized!")
            
            self.is_initialized = True
            print("\n🎉 Commission AI Assistant is ready to use!")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            print(f"❌ Initialization failed: {str(e)}")
            return False
    
    def generate_sql_for_srf(self, srf_text, target=None):
        """
        SRF text থেকে SQL query generate করি
        """
        if not self.is_initialized:
            return {
                'success': False,
                'error': 'System not initialized. Please run initialize_system() first.'
            }
        
        try:
            print(f"\n🔍 Processing SRF request...")
            print(f"SRF length: {len(srf_text)} characters")
              # Step 1: Retrieve similar examples
            print("1️⃣ Finding similar examples...")
            context = self.rag_system.retrieve_context(srf_text, max_results=settings.MAX_RETRIEVAL_RESULTS)
            
            quality_analysis = self.rag_system.analyze_retrieval_quality(context)
            print(f"   Quality: {quality_analysis['quality']}")
            print(f"   Similar examples found: {context.get('total_similar_found', 0)}")
            
            # Step 2: Format context
            print("2️⃣ Preparing context for AI...")
            formatted_context = self.rag_system.format_context_for_llm(context,target)
            
            
            # Step 3: Generate SQL
            print("3️⃣ Generating SQL query...")
            generation_result = self.sql_generator.generate_sql_query(formatted_context,context)

            if generation_result.get('last_result') is not None:
                generation_result = generation_result['last_result']


            if not generation_result['success']:
                return {
                    'success': False,
                    'error': generation_result.get('error'),
                    'context_quality': quality_analysis
                }
            
            # Step 4: Validate
            print("4️⃣ Validating generated SQL...")
            sql_query =self.sql_generator.remove_outer_backticks(generation_result['response'])
            validation = self.sql_generator.validate_generated_sql(sql_query)
            
            print("✅ SQL generation completed!")
            
            return {
                'success': True,
                'generated_sql': sql_query,
                'validation': validation,
                'context_quality': quality_analysis,
                'similar_examples_count': context.get('total_similar_found', 0),
                'high_confidence_count': context.get('high_confidence_count', 0)
            }
            
        except Exception as e:
            logger.error(f"SQL generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    def extract_srf_metadata(self, srf_text):
        """
        Extract metadata from SRF text to determine what sections are present
        """
        metadata = {
            'has_detail_formats': False,
            'has_commission_name': False,
            'has_start_date': False,
            'has_end_date': False,
        }
        
        # Convert to lowercase for case-insensitive matching
        srf_lower = srf_text.lower()
        
        # Check for detail formats
        detail_indicators = [
            'details format','details format:','details format :','details format',
            'detail format','detail format:','detail format :','detail format',
            'detail formats','detail formats:','detail formats :','detail formats',
            'details formats','details formats:','details formats :','details formats'
        ]
        metadata['has_detail_formats'] = any(indicator in srf_lower for indicator in detail_indicators)
        
        # Check for other sections
        metadata['has_commission_name'] = 'commission name' in srf_lower
        metadata['has_start_date'] = 'start date' in srf_lower
        metadata['has_end_date'] = 'end date' in srf_lower
        
        return metadata

    def get_dynamic_sample_format(self, metadata):
        """
        Generate sample format based on metadata
        """
        base_format = """# Commission Business Logics: DD HIT Campaign_27th to 31st May25

        *Commission Name:* DD HIT Campaign_27th to 31st May25  
        *Start Date:* 27-May-2025  
        *End Date:* 31-May-2025  
        *Commission Receiver Channel:* Distributor
         *All calculation Conditions:*
            - Agent list of 31st May'25 will be considered
            - Distributor has a target and it will be given by Business Team
            - Selected Deno (709,699,798,899) will be considered for performance calculation.
            - General mathematical rounding: below 0.5 will be rounded down, ≥0.5 rounded up for achievement calculation.
            - Upon achieving Deno HIT target (Count of 709 denomination), Distributor will be given achievement-based incentives.
            - Maximum Achievement capping is 200%.
            - Achievement Slab:
                | Achievement        | Incentives     |
                |-------------------|---------------|
                | 200% and Above    | TARGET*2*50   |
                | 100% and Above    | HIT*50        |
                | Below 100%        | 0             |"""
        
        # Add detail formats only if present in SRF
        if metadata['has_detail_formats']:
            base_format += """

        *Detail formats:*
        - *Detail 1:* DD_CODE, TARGET, HIT, ACH_PER, COMMISSION
        - *Detail 2:* DD_CODE, RETAILER_CODE, RET_MSISDN, CUSTOMER_MSISDN,RECHARGE_AMOUNT"""
        
        return base_format

    def cleaned_srf_text(self, srf_text):
        """
        SRF text থেকে unnecessary characters remove করি
        """
        # Extract metadata to determine what sections to include
        metadata = self.extract_srf_metadata(srf_text)
        
        # Get dynamic sample format based on metadata
        sample_format = self.get_dynamic_sample_format(metadata)

        prompt = f""""
        <sample format>
        {sample_format}
        </sample format>

        <srf text>
        {srf_text} 
        </srf text>
        """
        
        system_prompt = """
        You are an expert in understanding SRF texts. Your job is to format <srf text> based on the <sample format> provided.        
        Do NOT include any information that are not present in <sample format>
        """
        
        result = self.sql_generator.call_openAI_API([   
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ])
        return result

    def get_system_status(self):
        """
        System status check করি
        """
        status = {
            'initialized': self.is_initialized,
            'components': {}
        }
        
        if self.embedding_manager:
            try:
                embedding_info = self.embedding_manager.get_collection_info()
                status['components']['embeddings'] = {
                    'status': 'ready',
                    'total_embeddings': embedding_info.get('total_embeddings', 0)
                }
            except:
                status['components']['embeddings'] = {'status': 'error'}
        
        if self.sql_generator:
            status['components']['sql_generator'] = {'status': 'ready'}
        
        if self.rag_system:
            status['components']['rag_system'] = {'status': 'ready'}
        
        return status

# Simple CLI interface
def run_cli_interface():
    """
    Simple command line interface
    """
    print("=" * 60)
    print("🤖 Commission AI Assistant - CLI Interface")
    print("=" * 60)
    
    assistant = CommissionAIAssistant()
    
    # Initialize system
    jsonl_path = input("\n📁 Enter path to your JSONL training data (or press Enter to skip): ").strip()
    if not jsonl_path:
        jsonl_path = None
    
    if not assistant.initialize_system(jsonl_path):
        print("❌ System initialization failed!")
        return
    
    # Main loop
    while True:
        print("\n" + "="*50)
        print("🎯 Choose an option:")
        print("1. Generate SQL from SRF")
        print("2. System Status")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            print("\n📝 Enter your SRF content:")
            srf_text = input().strip()
            
            if not srf_text:
                print("❌ Empty SRF text!")
                continue
            
            
            # Generate SQL
            result = assistant.generate_sql_for_srf(srf_text)
            
            print("\n" + "="*50)
            print("📊 RESULTS:")
            print("="*50)
            
            if result['success']:
                print("✅ SUCCESS!")
                print(f"\n🔍 Context Quality: {result['context_quality']['quality']}")
                print(f"📈 Similar Examples: {result['similar_examples_count']}")
                print(f"🎯 High Confidence: {result['high_confidence_count']}")
                
                print(f"\n💾 GENERATED SQL:")
                print("-" * 40)
                print(result['generated_sql'])
                print("-" * 40)
                
                validation = result['validation']
                if validation['is_valid']:
                    print("✅ Validation: PASSED")
                else:
                    print("⚠️  Validation Issues:")
                    for issue in validation['issues']:
                        print(f"   - {issue}")
                
                if validation['suggestions']:
                    print("💡 Suggestions:")
                    for suggestion in validation['suggestions']:
                        print(f"   - {suggestion}")
            else:
                print(f"❌ FAILED: {result['error']}")
        
        elif choice == '2':
            status = assistant.get_system_status()
            print("\n📊 System Status:")
            print(f"  Initialized: {'✅' if status['initialized'] else '❌'}")
            
            for component, info in status['components'].items():
                status_icon = '✅' if info['status'] == 'ready' else '❌'
                print(f"  {component}: {status_icon} {info['status']}")
                
                if 'total_embeddings' in info:
                    print(f"    Embeddings: {info['total_embeddings']}")
        
        elif choice == '3':
            print("\n👋 Thank you for using Commission AI Assistant!")
            break
        
        else:
            print("❌ Invalid choice! Please enter 1, 2, or 3.")

# Direct run করার জন্য
if __name__ == "__main__":
    try:
        run_cli_interface()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}")
