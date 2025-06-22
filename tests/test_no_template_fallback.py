"""
Test script to verify that template fallback is completely removed
and proper error messages are shown when AI fails
"""
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sql_generator import SQLGenerator

def test_no_template_fallback():
    """Test that template fallback is removed and proper errors are shown"""
    print("🧪 Testing No Template Fallback Mechanism")
    print("=" * 60)
    
    # Test 1: Invalid AI provider
    print("\n1️⃣ Testing Invalid AI Provider:")
    try:
        generator = SQLGenerator(ai_provider="invalid_provider")
        result = generator.generate_sql_query("Test SRF content")
        print(f"   Result: {result}")
        if not result['success'] and 'Unsupported AI provider' in result['error']:
            print("   ✅ Correctly shows error for invalid provider")
        else:
            print("   ❌ Should show error for invalid provider")
    except Exception as e:
        print(f"   ❌ Unexpected exception: {e}")
    
    # Test 2: OpenAI without API key
    print("\n2️⃣ Testing OpenAI without API Key:")
    try:
        # Temporarily remove API key
        original_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        generator = SQLGenerator(ai_provider="openai", api_key=None)
        result = generator.generate_sql_query("Test SRF content")
        print(f"   Result: {result}")
        if not result['success'] and 'API key' in result['error']:
            print("   ✅ Correctly shows error for missing API key")
        else:
            print("   ❌ Should show error for missing API key")
            
        # Restore API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
    except Exception as e:
        print(f"   ❌ Unexpected exception: {e}")
    
    # Test 3: Ollama with wrong URL
    print("\n3️⃣ Testing Ollama with Wrong URL:")
    try:
        generator = SQLGenerator(ai_provider="ollama", ollama_base_url="http://invalid:11434")
        result = generator.generate_sql_query("Test SRF content")
        print(f"   Result: {result}")
        if not result['success']:
            print("   ✅ Correctly shows error for invalid Ollama URL")
        else:
            print("   ❌ Should show error for invalid Ollama URL")
    except Exception as e:
        print(f"   ❌ Unexpected exception: {e}")
    
    # Test 4: Check that template generator is not used as fallback
    print("\n4️⃣ Testing No Template Fallback:")
    try:
        # Check if template_sql_generator is imported
        import importlib.util
        spec = importlib.util.find_spec("template_sql_generator")
        if spec is None:
            print("   ✅ template_sql_generator module not found - good!")
        else:
            # Check if SQLGenerator imports it
            with open("src/sql_generator.py", "r") as f:
                content = f.read()
                if "from template_sql_generator import" in content:
                    print("   ❌ SQLGenerator still imports template_sql_generator")
                else:
                    print("   ✅ SQLGenerator does not import template_sql_generator")
                    
                if "_generate_with_template" in content:
                    print("   ❌ SQLGenerator still has _generate_with_template method")
                else:
                    print("   ✅ SQLGenerator does not have _generate_with_template method")
    except Exception as e:
        print(f"   ⚠️  Could not check template imports: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Template fallback removal test completed!")
    print("💡 System should now show clear error messages instead of falling back to templates")

if __name__ == "__main__":
    test_no_template_fallback()
