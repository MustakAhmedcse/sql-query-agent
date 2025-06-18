"""
Configuration settings for Commission AI Assistant
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the base directory (parent of config directory)
BASE_DIR = Path(__file__).parent.parent.absolute()

# Load environment variables - try both locations
load_dotenv(".env")  # Root directory
load_dotenv("config/.env")  # Config directory (backup)

class Settings:
    """Application settings"""
      # Ollama Configuration
    OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # AI Provider (openai or ollama)
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # ChromaDB Configuration - use absolute path
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "embeddings"))
    
    # RAG Configuration
    MAX_RETRIEVAL_RESULTS = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    
    # Data Paths - use absolute paths
    TRAINING_DATA_PATH = str(BASE_DIR / "data" / "training_data")
    TEMPLATES_PATH = str(BASE_DIR / "data" / "templates")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Web App
    HOST = "0.0.0.0"
    PORT = 8000
    
# Create global settings instance
settings = Settings()
