# 🤖 Commission AI Assistant

An intelligent AI-powered system that generates SQL queries for MyBL Commission reports from SRF (Service Request Format) inputs using RAG (Retrieval-Augmented Generation) technology.

## 🎯 Project Overview

This system learns from historical SRF-SQL pairs and automatically generates accurate SQL queries for new SRF inputs. It uses advanced AI technologies including ChromaDB for vector storage, Sentence Transformers for embeddings, and supports both OpenAI and Ollama AI providers.

## ✨ Key Features

- **AI-Powered SQL Generation**: Supports OpenAI GPT and Ollama models
- **RAG Technology**: Retrieves similar examples for better context
- **File Upload Support**: Process SRF documents (.doc/.docx) and Excel files
- **Web Interface**: User-friendly web application
- **Real-time Processing**: Fast SQL generation with timing metrics
- **Error Handling**: Clear error messages with troubleshooting guidance

## 📁 Project Structure

```
Commission Agent/
├── src/
│   ├── data_processor.py      # Training data processing
│   ├── embedding_manager.py   # Vector embeddings management
│   ├── rag_system.py         # RAG implementation
│   ├── sql_generator.py      # AI-powered SQL generation
│   └── file_processor.py     # File upload processing
├── web/
│   ├── app.py               # FastAPI web application
│   └── templates/
│       └── index.html       # Web interface
├── config/
│   └── settings.py          # Application configuration
├── data/
│   ├── training_data/       # Processed training data
│   └── embeddings/          # ChromaDB vector storage
├── tests/                   # Test scripts
├── main.py                  # Main application entry point
├── run.py                   # Application runner
├── requirements.txt         # Python dependencies
└── .env                     # Environment configuration
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv commission_env

# Activate environment (Windows)
commission_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the project root:
```bash
# AI Provider Configuration
AI_PROVIDER=openai                    # Options: openai, ollama

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MODELS=gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-4,gpt-3.5-turbo

# Ollama Configuration (if using Ollama)
OLLAMA_API_BASE_URL=http://192.168.105.58:11434
OLLAMA_MODEL=qwen3
OLLAMA_MODELS=qwen3:4b-q8_0,llama3:8b,llama3:70b,codellama:7b,mistral:7b

# Embedding Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_DB_PATH=./data/embeddings

# RAG Settings
CONFIDENCE_THRESHOLD=0.7
MAX_RETRIEVAL_RESULTS=5
```

### 3. Initialize the System
```bash
# Run the main application to initialize
python main.py


```

### 4. Start Web Application
```bash
# Start the web interface
python run.py
# OR
python -m web.app
# OR
python run.py cli
```

Open your browser and go to `http://localhost:8000`

## 🔧 How It Works

1. **AI Provider Selection**: Choose between OpenAI GPT models or Ollama local models
2. **RAG Retrieval**: System finds similar SRF examples from training data
3. **Context Building**: Combines retrieved examples with your input
4. **AI Generation**: Uses selected AI model to generate SQL query
5. **Validation**: Validates the generated SQL for syntax and logic
6. **Error Handling**: Shows clear error messages if generation fails

## 📝 Usage

### Web Interface:
1. **Select AI Provider**: Choose OpenAI or Ollama from the dropdown
2. **Select Model**: Pick specific model for your provider
3. **Input SRF**: Either type directly or upload SRF documents (.doc/.docx)
4. **Supporting Info**: Optionally upload Excel/CSV files or add manual info
5. **Generate SQL**: Click the generate button
6. **Review Results**: Check the generated SQL and validation results

### File Upload Support:
- **SRF Documents**: Upload .doc or .docx files for automatic text extraction
- **Supporting Data**: Upload .xlsx, .xls, or .csv files for additional context

## 🧪 Testing

Run the test scripts in the `tests/` folder:
```bash
# Test AI provider configuration
python tests/test_ai_provider.py

# Test without template fallback
python tests/test_no_template_fallback.py
```

## ⚙️ AI Provider Setup

### For OpenAI:
1. Get API key from OpenAI
2. Set `AI_PROVIDER=openai` in .env
3. Add your `OPENAI_API_KEY` to .env

### For Ollama:
1. Install and run Ollama server
2. Set `AI_PROVIDER=ollama` in .env
3. Configure `OLLAMA_API_BASE_URL` in .env

## 🚨 Error Handling

The system provides clear error messages for:
- Missing or invalid API keys
- Unreachable AI servers
- Network connectivity issues
- Invalid configuration settings
- Unsupported file formats

No template fallbacks - you get honest feedback about AI capabilities.

## 📊 Features

- ✅ **Dual AI Support**: OpenAI GPT and Ollama models
- ✅ **File Processing**: SRF documents and Excel/CSV uploads
- ✅ **Real-time Generation**: Fast SQL generation with timing metrics
- ✅ **Quality Metrics**: Context quality and confidence scoring
- ✅ **Validation**: SQL syntax and logic validation
- ✅ **Error Transparency**: Clear error messages without hidden fallbacks
- ✅ **Web Interface**: Professional, user-friendly design

## 🎯 Perfect for POCs

This system is designed for commission POC projects where:
- Multiple commission types need to be handled
- AI transparency is important
- Clear error feedback is required
- No assumptions about template coverage should be made

## 📞 Support

For issues or questions, check the error messages in the web interface - they include troubleshooting guidance for common problems.
