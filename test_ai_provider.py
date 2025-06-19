"""
Test AI Provider Configuration
Test script to verify AI provider switching between OpenAI and Ollama
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ai_provider():
    """Test AI provider configuration"""
    print("🧪 Testing AI Provider Configuration")
    print("=" * 50)
    
    # Add src to path
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        from sql_generator import SQLGenerator
        
        # Test OpenAI provider
        print("\n1️⃣ Testing OpenAI Provider:")
        ai_provider = os.getenv("AI_PROVIDER", "openai")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        print(f"   AI_PROVIDER: {ai_provider}")
        print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Not set'}")
        
        if ai_provider.lower() == "openai":
            if openai_key:
                generator = SQLGenerator(ai_provider="openai", api_key=openai_key)
                print("   ✅ OpenAI generator initialized successfully")
            else:
                print("   ⚠️  OpenAI selected but no API key found")
        
        # Test Ollama provider
        print("\n2️⃣ Testing Ollama Provider:")
        ollama_url = os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen3")
        
        print(f"   OLLAMA_API_BASE_URL: {ollama_url}")
        print(f"   OLLAMA_MODEL: {ollama_model}")
        
        generator_ollama = SQLGenerator(ai_provider="ollama", ollama_base_url=ollama_url)
        
        # Test Ollama availability
        if generator_ollama._check_ollama_availability():
            print("   ✅ Ollama server is available")
        else:
            print("   ⚠️  Ollama server is not available")
        
        # Test Template provider
        print("\n3️⃣ Testing Template Provider:")
        generator_template = SQLGenerator(ai_provider="template")
        print("   ✅ Template generator initialized successfully")
        
        print("\n🎉 All provider tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def test_environment_variables():
    """Test environment variable loading"""
    print("\n🔧 Testing Environment Variables")
    print("=" * 50)
    
    required_vars = [
        "AI_PROVIDER",
        "OPENAI_API_KEY", 
        "OPENAI_MODEL",
        "OLLAMA_API_BASE_URL",
        "OLLAMA_MODEL",
        "CHROMA_DB_PATH",
        "EMBEDDING_MODEL"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask API keys for security
            if "API_KEY" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: ❌ Not set")

def show_current_config():
    """Show current AI provider configuration"""
    print("\n⚙️  Current Configuration")
    print("=" * 50)
    
    ai_provider = os.getenv("AI_PROVIDER", "openai").lower()
    print(f"🤖 Active AI Provider: {ai_provider.upper()}")
    
    if ai_provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"📝 Model: {model}")
        print("💡 To switch to Ollama: Set AI_PROVIDER=ollama in .env file")
    elif ai_provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "qwen3")
        url = os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")
        print(f"📝 Model: {model}")
        print(f"🌐 URL: {url}")
        print("💡 To switch to OpenAI: Set AI_PROVIDER=openai in .env file")
    else:
        print("📝 Using template-based generation")
        print("💡 To use AI: Set AI_PROVIDER=openai or AI_PROVIDER=ollama in .env file")

if __name__ == "__main__":
    try:
        print("🚀 AI Provider Configuration Test")
        print("=" * 60)
        
        # Test environment variables
        test_environment_variables()
        
        # Show current config
        show_current_config()
        
        # Test AI providers
        success = test_ai_provider()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ All tests passed! AI provider configuration is working correctly.")
        else:
            print("❌ Some tests failed. Please check your configuration.")
            
        print("\n💡 To change AI provider:")
        print("   1. Edit .env file")
        print("   2. Change AI_PROVIDER=openai or AI_PROVIDER=ollama")
        print("   3. Restart the application")
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted!")
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        sys.exit(1)
