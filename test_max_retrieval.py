"""
Quick test to verify MAX_RETRIEVAL_RESULTS is working
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import configuration
from config.settings import settings

def test_max_retrieval_results():
    """Test if MAX_RETRIEVAL_RESULTS is loaded correctly"""
    print("🧪 Testing MAX_RETRIEVAL_RESULTS Configuration")
    print("=" * 50)
    
    print(f"Environment Variable: {os.getenv('MAX_RETRIEVAL_RESULTS')}")
    print(f"Settings Value: {settings.MAX_RETRIEVAL_RESULTS}")
    print(f"Type: {type(settings.MAX_RETRIEVAL_RESULTS)}")
    
    if settings.MAX_RETRIEVAL_RESULTS == 2:
        print("✅ MAX_RETRIEVAL_RESULTS is correctly set to 2")
        return True
    else:
        print(f"❌ Expected 2, but got {settings.MAX_RETRIEVAL_RESULTS}")
        return False

if __name__ == "__main__":
    test_max_retrieval_results()
