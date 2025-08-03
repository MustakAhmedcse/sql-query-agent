#!/usr/bin/env python3
"""
Command Line Interface for Commission SQL Generator
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from orchestrator import CommissionSQLOrchestrator
from models import CommissionState

def load_srf_from_file(file_path: str) -> str:
    """Load SRF requirements from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error loading SRF file: {e}")
        sys.exit(1)

def load_schemas_from_file(file_path: str) -> dict:
    """Load table schemas from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading schemas file: {e}")
        sys.exit(1)

def save_outputs(result: CommissionState, output_dir: str):
    """Save all outputs to specified directory"""
    try:
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save SQL script
        if result["final_script"]:
            sql_file = Path(output_dir) / "commission_calculation.sql"
            with open(sql_file, 'w', encoding='utf-8') as f:
                f.write(result["final_script"])
            print(f"📄 SQL script saved to: {sql_file}")
        
        # Save report
        if result["summary_report"]:
            report_file = Path(output_dir) / "generation_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(result["summary_report"])
            print(f"📊 Report saved to: {report_file}")
        
        # Save metadata
        if result["metadata"]:
            metadata_file = Path(output_dir) / "extracted_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(result["metadata"], f, indent=2)
            print(f"📋 Metadata saved to: {metadata_file}")
        
        # Save step details
        if result["sql_steps"]:
            steps_file = Path(output_dir) / "sql_steps.json"
            steps_data = [
                {
                    "step_number": step.step_number,
                    "name": step.name,
                    "description": step.description,
                    "sql_query": step.sql_query,
                    "depends_on": step.depends_on,
                    "validation_query": step.validation_query
                }
                for step in result["sql_steps"]
            ]
            with open(steps_file, 'w', encoding='utf-8') as f:
                json.dump(steps_data, f, indent=2)
            print(f"🔧 Steps details saved to: {steps_file}")
        
    except Exception as e:
        print(f"❌ Error saving outputs: {e}")

def print_summary(result: CommissionState):
    """Print generation summary"""
    print("\n" + "="*60)
    print("📊 GENERATION SUMMARY")
    print("="*60)
    
    metadata = result["metadata"]
    print(f"Commission Name: {metadata.get('commission_name', 'Unknown')}")
    print(f"Campaign Period: {metadata.get('start_date')} to {metadata.get('end_date')}")
    print(f"Receiver Channel: {metadata.get('receiver_channel')}")
    print(f"Total SQL Steps: {len(result['sql_steps'])}")
    print(f"Warnings: {len(result['warnings'])}")
    print(f"Errors: {len(result['errors'])}")
    
    if result["warnings"]:
        print("\n⚠️ WARNINGS:")
        for warning in result["warnings"]:
            print(f"  - {warning}")
    
    if result["errors"]:
        print("\n❌ ERRORS:")
        for error in result["errors"]:
            print(f"  - {error}")
    
    print("\n✅ Generation completed successfully!")

def generate_command(args):
    """Handle generate command"""
    print("🚀 Starting commission SQL generation...")
    
    # Load SRF
    if args.srf_file:
        srf_text = load_srf_from_file(args.srf_file)
    else:
        srf_text = args.srf_text
    
    if not srf_text:
        print("❌ No SRF requirements provided. Use --srf-file or --srf-text")
        sys.exit(1)
    
    # Load schemas if provided
    table_schemas = None
    if args.schemas_file:
        table_schemas = load_schemas_from_file(args.schemas_file)
    
    # Initialize orchestrator
    try:
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI API key required. Use --api-key or set OPENAI_API_KEY environment variable")
            sys.exit(1)
        
        orchestrator = CommissionSQLOrchestrator(openai_api_key=api_key)
        
        # Generate SQL
        print("🔍 Processing SRF requirements...")
        result = orchestrator.process_srf(srf_text, table_schemas)
        
        # Save outputs
        output_dir = args.output_dir or f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_outputs(result, output_dir)
        
        # Print summary
        print_summary(result)
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        sys.exit(1)

def execute_command(args):
    """Handle execute command - REMOVED"""
    print("❌ SQL execution functionality has been removed from this version.")
    print("🔄 Use the generated SQL scripts directly in your database client.")
    sys.exit(1)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Commission SQL Generator - Generate step-by-step SQL for commission calculations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate SQL from SRF file
  python cli.py generate --srf-file srf_requirements.txt --api-key sk-xxx --output-dir output

  # Generate SQL from text
  python cli.py generate --srf-text "Commission Name: Test..." --api-key sk-xxx

  # Note: SQL execution has been removed. Use generated scripts directly in your database client.
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate SQL from SRF requirements')
    generate_parser.add_argument('--srf-file', help='Path to SRF requirements file')
    generate_parser.add_argument('--srf-text', help='SRF requirements as text')
    generate_parser.add_argument('--schemas-file', help='Path to table schemas JSON file')
    generate_parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    generate_parser.add_argument('--output-dir', help='Output directory (default: output_YYYYMMDD_HHMMSS)')
    
    # Execute command (disabled)
    execute_parser = subparsers.add_parser('execute', help='[DISABLED] Execute generated SQL steps')
    execute_parser.add_argument('--steps-file', help='[DISABLED] Path to sql_steps.json file')
    execute_parser.add_argument('--db-connection', help='[DISABLED] Database connection string')
    execute_parser.add_argument('--output-dir', help='[DISABLED] Output directory')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        generate_command(args)
    elif args.command == 'execute':
        execute_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
