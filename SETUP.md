# Quick Setup Guide - Commission AI Assistant

## 🚀 দ্রুত শুরুর গাইড

### 1. Prerequisites চেক করুন:
- ✅ Python 3.7+ installed
- ✅ Ollama server running at http://27.147.159.197:11434  
- ✅ Qwen3 model available in Ollama
- ✅ Your training data (srf_sql_pairs.jsonl) ready

### 2. সহজ Setup (Windows):
```cmd
# ⚠️ If you get dependency errors, use INSTALL_MANUAL.md

# Quick start (may need troubleshooting)
start.bat

# Or manual setup (recommended):
python -m venv commission_env
commission_env\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install fastapi uvicorn pydantic requests pandas
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install transformers sentence-transformers chromadb ollama
```

### 3. Manual Setup:
```cmd
# 1. Virtual environment তৈরি করুন
python -m venv commission_env

# 2. Activate করুন  
commission_env\Scripts\activate

# 3. Dependencies install করুন
pip install -r requirements.txt

# 4. Training data setup করুন (first time only)
python run.py setup

# 5. Web interface চালান
python run.py web
```

### 4. ব্যবহার:
- 🌐 Web Interface: http://localhost:8000
- 💻 CLI Interface: `python run.py cli`

### 5. Common Issues:

**Issue: "Import could not be resolved"**
- Solution: Dependencies install করুন `pip install -r requirements.txt`

**Issue: "Ollama connection failed"**
- Solution: Ollama server চালু আছে কিনা check করুন

**Issue: "No training data found"**  
- Solution: `python run.py setup` চালান

**Issue: "Model not found"**
- Solution: Ollama তে Qwen3 model install করুন

### 6. File Structure Check:
```
Commission Agent/
├── src/                 ✅ Core modules
├── web/                 ✅ Web interface  
├── config/              ✅ Configuration
├── data/                ✅ Training data
├── requirements.txt     ✅ Dependencies
├── run.py              ✅ Main runner
└── start.bat           ✅ Quick start
```

### 7. Test করার জন্য:
1. `python run.py setup` - Data setup test
2. `python run.py web` - Web interface test  
3. Browser এ http://localhost:8000 open করুন
4. Sample SRF দিয়ে test করুন

### 8. Production এ deploy করার জন্য:
- Environment variables properly set করুন
- Ollama server stable connection ensure করুন  
- Training data regularly update করুন
- User feedback integrate করুন

---
🎯 **Quick Start Command**: `start.bat` (Windows) বা `python run.py web`
