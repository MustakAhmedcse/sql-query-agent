# 🤖 Commission AI Assistant

একটি RAG-based AI system যা MyBL Commission এর জন্য SRF input নিয়ে SQL query generate করে।

## 🎯 Project Overview

এই system টি আপনার historical SRF-SQL pairs থেকে শিখে নতুন SRF দিলে automatically SQL query generate করবে। এটি high accuracy এর জন্য ChromaDB, Sentence Transformers এবং Ollama Qwen3 model ব্যবহার করে।

## 📁 Project Structure

```
Commission Agent/
├── data/
│   ├── training_data/      # আপনার SRF-SQL pairs
│   ├── embeddings/         # ChromaDB storage
│   └── templates/          # SQL templates
├── src/
│   ├── data_processor.py   # Data processing
│   ├── embedding_manager.py # Embedding management
│   ├── rag_system.py       # RAG implementation
│   ├── sql_generator.py    # SQL generation
│   ├── validator.py        # Query validation
│   └── main.py            # Main application
├── config/
│   ├── settings.py        # Configuration
│   └── .env              # Environment variables
├── web/
│   ├── app.py            # Web interface
│   └── templates/        # HTML templates
├── requirements.txt      # Dependencies
├── README.md            # This file
└── run.py              # Application runner
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Virtual environment তৈরি করুন
python -m venv commission_env

# Activate করুন (Windows)
commission_env\Scripts\activate

# Dependencies install করুন
pip install -r requirements.txt
```

### 2. Configuration
```bash
# .env file তৈরি করুন
OLLAMA_API_BASE_URL=http://27.147.159.197:11434
OLLAMA_MODEL=qwen3
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_DB_PATH=./data/embeddings
```

### 3. Data Preparation
```bash
# আপনার existing data load করুন
python src/data_processor.py

# Embeddings generate করুন
python src/embedding_manager.py
```

### 4. Run Application
```bash
# Web interface চালান
python run.py
```

আপনার browser এ `http://localhost:8000` এ যান।

## 🔧 How It Works

1. **Data Processing**: আপনার SRF-SQL pairs process করে
2. **Embedding Generation**: ChromaDB তে semantic embeddings store করে
3. **RAG Retrieval**: নতুন SRF এর জন্য similar examples খুঁজে
4. **SQL Generation**: Qwen3 model দিয়ে SQL query generate করে
5. **Validation**: Generated query validate করে
6. **Learning**: User feedback থেকে শিখে

## 📝 Usage

### SRF Input করার জন্য:
1. Web interface এ SRF text paste করুন
2. Supporting table format specify করুন
3. "Generate SQL" button click করুন
4. Generated query review করুন
5. Feedback দিন accuracy improve করার জন্য

### API Usage:
```python
import requests

response = requests.post("http://localhost:8000/generate-sql", 
    json={
        "srf_text": "আপনার SRF content",
        "supporting_format": "table structure"
    })

sql_query = response.json()["generated_sql"]
```

## 🎯 Features

- ✅ High accuracy SQL generation
- ✅ Historical data থেকে learning
- ✅ User feedback integration
- ✅ Query validation
- ✅ Web-based interface
- ✅ API endpoints
- ✅ Continuous improvement

## 📊 Accuracy Improvement

System টি এই strategies ব্যবহার করে high accuracy ensure করে:

1. **Multi-layered Retrieval**: Semantic + keyword + pattern matching
2. **Template-based Generation**: Common patterns extract করে
3. **Validation Pipeline**: Multiple validation layers
4. **Continuous Learning**: User feedback integration
5. **Business Logic Encoding**: Domain-specific rules

## 🔄 Training Process

1. আপনার existing SRF-SQL pairs load করুন
2. Data preprocessing ও cleaning
3. Embedding generation ও storage
4. Pattern extraction ও template creation
5. Model fine-tuning (optional)

## 🐛 Troubleshooting

### Common Issues:
- **Ollama connection error**: Check OLLAMA_API_BASE_URL
- **ChromaDB issues**: Delete embeddings folder and regenerate
- **Low accuracy**: Add more training data or adjust retrieval parameters

## 🤝 Contributing

1. নতুন SRF-SQL pairs add করুন training data তে
2. Business logic improve করুন
3. Validation rules enhance করুন
4. Bug reports ও feedback দিন

## 📞 Support

কোন সমস্যা হলে documentation check করুন অথবা issue create করুন।

---

**Note**: এই system টি আপনার specific MyBL Commission requirements এর জন্য তৈরি। High accuracy এর জন্য আপনার historical data quality important।
