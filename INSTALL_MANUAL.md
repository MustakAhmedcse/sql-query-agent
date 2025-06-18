# 🔧 Manual Installation Guide - Windows

## ❌ Dependencies Install Error Solution

যদি `start.bat` এ error আসে, তাহলে manual installation করুন:

### Step 1: Environment Check
```cmd
# Python version check (3.8+ লাগবে)
python --version

# Pip check
python -m pip --version
```

### Step 2: Virtual Environment
```cmd
# Project folder এ যান
cd "d:\SalesCom Agent\Commission Agent"

# Virtual environment তৈরি করুন
python -m venv commission_env

# Activate করুন
commission_env\Scripts\activate
```

### Step 3: Pip Upgrade (Important!)
```cmd
# First pip, setuptools, wheel upgrade করুন
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools wheel
```

### Step 4: Dependencies Install (Step by Step)
```cmd
# Core web framework
python -m pip install fastapi uvicorn pydantic

# Basic utilities
python -m pip install requests numpy pandas

# AI libraries (torch first)
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install transformers sentence-transformers

# ChromaDB and Ollama
python -m pip install chromadb ollama

# Data processing
python -m pip install openpyxl python-docx PyPDF2

# Web utilities
python -m pip install python-multipart jinja2 python-dotenv
```

### Step 5: Verify Installation
```cmd
# Test imports
python -c "import fastapi; print('FastAPI OK')"
python -c "import sentence_transformers; print('Sentence Transformers OK')"
python -c "import chromadb; print('ChromaDB OK')"
python -c "import ollama; print('Ollama OK')"
```

### Step 6: Alternative Minimal Setup
যদি AI libraries install না হয়, তাহলে minimal version দিয়ে start করুন:

```cmd
# শুধু core dependencies
python -m pip install fastapi uvicorn pydantic requests pandas openpyxl python-docx python-multipart jinja2 python-dotenv

# Simple text processing version use করুন
```

## 🚀 Quick Start After Installation

### Option A: Web Interface
```cmd
python run.py web
# Browser এ http://localhost:8000 খুলুন
```

### Option B: CLI Interface  
```cmd
python run.py cli
```

### Option C: Setup Training Data
```cmd
python run.py setup
```

## 🐛 Common Issues & Solutions

### Issue 1: "Cannot import 'setuptools.build_meta'"
**Solution:**
```cmd
python -m pip install --upgrade setuptools pip wheel
```

### Issue 2: "Microsoft Visual C++ 14.0 is required"
**Solution:** 
- Install Visual Studio Build Tools
- অথবা pre-compiled wheels use করুন:
```cmd
python -m pip install --only-binary=all sentence-transformers
```

### Issue 3: Torch installation failed
**Solution:**
```cmd
# CPU version install করুন
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue 4: ChromaDB issues
**Solution:**
```cmd
# Alternative version try করুন
python -m pip install chromadb==0.3.29
```

## 🎯 Minimal Working Version

যদি সব dependencies install না হয়, basic version দিয়ে start করতে পারেন:

```python
# শুধু text processing + Ollama দিয়ে
# AI embeddings ছাড়াই keyword-based search করে
```

## 🔄 Step-by-Step Troubleshooting

1. **Python Version**: 3.8+ হতে হবে
2. **Pip Upgrade**: Latest pip version লাগবে
3. **Virtual Environment**: Fresh environment তৈরি করুন
4. **Dependencies**: One by one install করুন
5. **Test**: প্রতিটি component test করুন

## 📞 Alternative Quick Start

যদি installation complex লাগে:

1. শুধু core dependencies install করুন
2. Basic text matching দিয়ে start করুন  
3. Gradually advanced features add করুন

```cmd
# Minimal start
python -m pip install fastapi uvicorn requests pandas
python run.py web
```

---

**💡 Tip**: Installation এ সমস্যা হলে step-by-step approach নিন। সব features একসাথে install করার চেষ্টা না করে core features দিয়ে start করুন।
