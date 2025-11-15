# 🚀 Quick Start Guide

## Prerequisites Check
```bash
python test_setup.py
```

## 1. Setup Environment (30 seconds)

```bash
# Copy template
cp env.template .env

# Edit .env with your:
# - PostgreSQL credentials
# - OpenAI API key
```

## 2. Install Dependencies (2 minutes)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
pip install -r requirements-frontend.txt
```

## 3. Start Services

### Terminal 1 - Backend
```bash
cd backend
python main.py
```
✅ Backend running at http://localhost:8000

### Terminal 2 - Frontend
```bash
streamlit run frontend/app.py
```
✅ Frontend running at http://localhost:8501

## 4. Test It!

Open http://localhost:8501 and try:
- "Show all abnormal tests for Lab 12 yesterday"
- "How many reports were generated this month?"

## 🐳 Docker Alternative

```bash
docker-compose up -d
```

## 📚 More Help

See `SETUP.md` for detailed setup  
See `README.md` for full documentation

