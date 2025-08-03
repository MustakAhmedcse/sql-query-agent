#!/usr/bin/env python3
"""
Debug helper script for Commission SQL Generator
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check the development environment"""
    print("🔧 Development Environment Check")
    print("=" * 50)
    
    # Python version
    print(f"🐍 Python Version: {sys.version}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"📦 Python Path: {sys.executable}")
    
    # Environment variables
    print("\n🌍 Environment Variables:")
    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Not Set'}")
    
    if openai_key:
        print(f"   Key Preview: {openai_key[:10]}...{openai_key[-4:]}")
    
    # Check required files
    print("\n📄 Required Files:")
    required_files = [
        "orchestrator.py",
        "sql_generators.py", 
        "models.py",
        "cli.py",
        "api.py",
        "sample_srf.txt",
        "sample_schemas.json",
        "requirements.txt"
    ]
    
    for file in required_files:
        exists = Path(file).exists()
        print(f"   {file}: {'✅' if exists else '❌'}")
    
    # Check dependencies
    print("\n📦 Dependencies Check:")
    dependencies = [
        "langgraph",
        "langchain",
        "langchain_openai",
        "fastapi",
        "pydantic"
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"   {dep}: ✅ Installed")
        except ImportError:
            print(f"   {dep}: ❌ Missing")
    
    print("\n" + "=" * 50)
    print("Environment check completed!")

def test_basic_imports():
    """Test basic imports"""
    print("\n🧪 Testing Basic Imports")
    print("-" * 30)
    
    try:
        from models import CommissionState, SQLStep
        print("✅ Models imported successfully")
    except Exception as e:
        print(f"❌ Models import failed: {e}")
    
    try:
        # Skip LangGraph imports if not installed
        print("⚠️  Skipping LangGraph imports (expected if dependencies not installed)")
    except Exception as e:
        print(f"❌ LangGraph import failed: {e}")

def create_debug_srf():
    """Create a simple SRF for debugging"""
    debug_srf = """
    Commission Name: Debug Test Campaign
    Start Date: 2024-08-01
    End Date: 2024-08-31
    Commission Receiver Channel: Distributor

    Commission Business Logics:
    - KPI: Deno Recharge
    - Target: Simple target achievement
    - Mapping: Agent list mapping
    - Selected Deno (199, 299, 399) for testing
    - Basic commission calculation
    """
    
    with open("debug_srf.txt", "w") as f:
        f.write(debug_srf)
    
    print("📝 Created debug_srf.txt for testing")

def main():
    """Main debug function"""
    print("🚀 Commission SQL Generator - Debug Helper")
    
    check_environment()
    test_basic_imports()
    create_debug_srf()
    
    print("\n🎯 Debug Configurations Available:")
    print("1. Debug CLI - Generate SQL")
    print("2. Debug CLI - Generate with Schemas") 
    print("3. Debug FastAPI Server")
    print("4. Debug Orchestrator Directly")
    print("5. Debug Test Demo")
    print("6. Debug SQL Generators")
    print("7. Debug with Custom SRF Text")
    print("8. Debug - Current File")
    
    print("\n💡 Tips:")
    print("- Set OPENAI_API_KEY environment variable")
    print("- Install dependencies: pip install -r requirements.txt")
    print("- Use F5 to start debugging with selected configuration")
    print("- Check .vscode/launch.json for all debug configurations")

if __name__ == "__main__":
    main()
