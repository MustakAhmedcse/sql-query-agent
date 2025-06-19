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


class Settings:
    """Application settings"""
    
    # =============================================================================
    # AI PROVIDER CONFIGURATION
    # =============================================================================
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()
    
    # =============================================================================
    # OPENAI CONFIGURATION
    # =============================================================================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MODELS = [model.strip() for model in os.getenv("OPENAI_MODELS", "gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-4,gpt-3.5-turbo").split(",")]
    
    # =============================================================================
    # OLLAMA CONFIGURATION
    # =============================================================================
    OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", "http://192.168.105.58:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3")
    OLLAMA_MODELS = [model.strip() for model in os.getenv("OLLAMA_MODELS", "qwen3:4b-q8_0,llama3:8b,llama3:70b,codellama:7b,mistral:7b,phi3:mini").split(",")]
    
    # =============================================================================
    # EMBEDDING CONFIGURATION
    # =============================================================================
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    # ChromaDB Configuration - use absolute path
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "embeddings"))
    
    # =============================================================================
    # RAG CONFIGURATION
    # =============================================================================
    MAX_RETRIEVAL_RESULTS = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    
    # =============================================================================
    # DATA PATHS
    # =============================================================================
    # Data Paths - use absolute paths
    TRAINING_DATA_PATH = str(BASE_DIR / "data" / "training_data")
    TEMPLATES_PATH = str(BASE_DIR / "data" / "templates")
    
    # =============================================================================
    # LOGGING CONFIGURATION
    # =============================================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # =============================================================================
    # WEB APP CONFIGURATION
    # =============================================================================
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

# Create global settings instance
settings = Settings()
