"""
Test Script - Commission AI Assistant testing এর জন্য
"""
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_data_processing():
    """Data processing test করি"""
    print("🧪 Testing Data Processing...")
    
    try:
        from data_processor import DataProcessor
        
        # Test with sample data
        sample_data = [
            {
                "srf": "Commission calculation for MyBL campaign Period: 1st to 15th Apr 2025",
                "sql": "SELECT * FROM commission_table WHERE date BETWEEN '2025-04-01' AND '2025-04-15'",
                "supporting_table": "commission_table: msisdn, amount, date"
            }
        ]
        
        processor = DataProcessor()
        processed = processor.clean_and_process_data(sample_data)
        
        if processed:
            print("✅ Data processing test passed!")
            return True
        else:
            print("❌ Data processing test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Data processing test error: {str(e)}")
        return False

def test_ollama_connection():
    """Ollama connection test করি"""
    print("🧪 Testing Ollama Connection...")
    
    try:
        from sql_generator import SQLGenerator
        
        generator = SQLGenerator()
        
        # Simple test
        test_prompt = "Generate a simple SELECT statement"
        result = generator.generate_sql_query(test_prompt)
        
        if result['success']:
            print("✅ Ollama connection test passed!")
            return True
        else:
            print(f"❌ Ollama connection test failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Ollama connection test error: {str(e)}")
        return False

def test_embedding_setup():
    """Embedding setup test করি"""
    print("🧪 Testing Embedding Setup...")
    
    try:
        from embedding_manager import EmbeddingManager
        
        # Test initialization
        manager = EmbeddingManager()
        info = manager.get_collection_info()
        
        if info:
            print(f"✅ Embedding setup test passed! Total embeddings: {info.get('total_embeddings', 0)}")
            return True
        else:
            print("❌ Embedding setup test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Embedding setup test error: {str(e)}")
        return False

def test_complete_workflow():
    """Complete workflow test করি"""
    print("🧪 Testing Complete Workflow...")
    
    try:
        # Test SRF
        test_srf = """
        Commission Calculation Report for MyBL Campaign
        Period: 1st to 15th April 2025  
        Commission Type: Hourly Commission
        Rate: 2% of revenue
        Target: Active MSISDN with data usage
        """
        
        from main import CommissionAIAssistant
        
        assistant = CommissionAIAssistant()
        
        # Check if system is ready
        if not os.path.exists("./data/training_data/processed_training_data.json"):
            print("⚠️  Training data not found. Run setup first.")
            return False
        
        # Initialize
        if not assistant.initialize_system():
            print("❌ System initialization failed!")
            return False
        
        # Generate SQL
        result = assistant.generate_sql_for_srf(test_srf)
        
        if result['success']:
            print("✅ Complete workflow test passed!")
            print(f"Generated SQL: {result['generated_sql'][:100]}...")
            return True
        else:
            print(f"❌ Complete workflow test failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Complete workflow test error: {str(e)}")
        return False

def run_all_tests():
    """সব tests চালাই"""
    print("=" * 60)
    print("🧪 Commission AI Assistant - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Data Processing", test_data_processing),
        ("Ollama Connection", test_ollama_connection), 
        ("Embedding Setup", test_embedding_setup),
        ("Complete Workflow", test_complete_workflow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! System is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
    
    return passed == len(results)

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Tests interrupted!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        sys.exit(1)
