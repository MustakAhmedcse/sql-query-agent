"""
Application Runner - Commission AI Assistant চালানোর জন্য
Simple entry point for both CLI and Web interface
"""
import os
import sys
import argparse

def run_cli():
    """CLI interface চালান"""
    try:
        from main import run_cli_interface
        run_cli_interface()
    except ImportError:
        print("❌ Error: Required modules not found. Please install dependencies:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error running CLI: {str(e)}")

def run_web():
    """Web interface চালান"""
    try:
        from web.app import run_web_app
        run_web_app()
    except ImportError:
        print("❌ Error: Required modules not found. Please install dependencies:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error running web app: {str(e)}")

def setup_data():
    """Training data setup করুন"""
    try:
        print("🔧 Setting up training data...")
        
        # Check if source data exists
        source_file = "../MyBL_FEB_MAR_APR_MAY_25/srf_sql_pairs.jsonl"
        if not os.path.exists(source_file):
            print(f"❌ Source data file not found: {source_file}")
            print("Please ensure your training data file exists at the correct location.")
            return
        
        # Import and run data processor
        sys.path.append('src')
        from data_processor import process_your_data
        
        result = process_your_data(source_file)
        
        if result:
            print("✅ Training data setup completed!")
            print(f"Processed {len(result)} SRF-SQL pairs")
            
            # Setup embeddings
            print("\n🔧 Setting up embeddings...")
            from embedding_manager import setup_embeddings_from_processed_data
            
            processed_file = "./data/training_data/processed_training_data.json"
            manager = setup_embeddings_from_processed_data(processed_file)
            
            if manager:
                print("✅ Embeddings setup completed!")
                print("\n🎉 System is ready to use!")
                print("Run 'python run.py web' to start the web interface")
                print("Or run 'python run.py cli' for command line interface")
            else:
                print("❌ Embeddings setup failed!")
        else:
            print("❌ Training data setup failed!")
            
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Please install dependencies: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Setup error: {str(e)}")

def show_help():
    """Help information দেখান"""
    help_text = """
🤖 Commission AI Assistant

USAGE:
  python run.py [command]

COMMANDS:
  web       Start web interface (recommended)
  cli       Start command line interface  
  setup     Setup training data and embeddings
  help      Show this help message

EXAMPLES:
  python run.py web      # Start web app on http://localhost:8000
  python run.py cli      # Start command line interface
  python run.py setup    # Setup training data first time

FIRST TIME SETUP:
  1. Install dependencies: pip install -r requirements.txt
  2. Setup training data: python run.py setup  
  3. Start application: python run.py web

SYSTEM REQUIREMENTS:
  - Python 3.7+
  - Ollama server running at http://192.168.105.58:11434
  - Qwen3 model available in Ollama
  - Training data file: srf_sql_pairs.jsonl

For more information, check README.md
"""
    print(help_text)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Commission AI Assistant",
        add_help=False
    )
    parser.add_argument('command', nargs='?', default='help', 
                       choices=['web', 'cli', 'setup', 'help'],
                       help='Command to run')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 Commission AI Assistant")
    print("=" * 60)
    
    if args.command == 'web':
        print("🌐 Starting Web Interface...")
        run_web()
        
    elif args.command == 'cli':
        print("💻 Starting CLI Interface...")
        run_cli()
        
    elif args.command == 'setup':
        print("🔧 Starting Setup...")
        setup_data()
        
    elif args.command == 'help':
        show_help()
        
    else:
        print("❌ Unknown command. Use 'help' to see available commands.")
        show_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
