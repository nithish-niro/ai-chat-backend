# 🚀 Deployment Guide - Free Hosting Options

## Option 1: **Render.com** (Recommended - Easy & Free)

### Steps:
1. **Sign up** at https://render.com (free tier available)
2. **Push code to GitHub**:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ai-chat-backend.git
   git push -u origin main
   ```

3. **Create `render.yaml`** in project root:
   ```yaml
   services:
     - type: web
       name: lab-chatbot-backend
       runtime: python
       runtimeVersion: 3.13.9
       plan: free
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
       envVars:
         - key: DB_HOST
           value: ${DB_HOST}
         - key: DB_PORT
           value: 5432
         - key: DB_NAME
           value: analyticaldata
         - key: DB_USER
           value: postgres
         - key: DB_PASSWORD
           fromFile: .env
         - key: OPENAI_API_KEY
           fromFile: .env
         - key: LLM_MODEL
           value: gpt-4o-mini
   ```

4. **In Render Dashboard**:
   - Click "New" → "Web Service"
   - Connect GitHub repo
   - Select `render.yaml`
   - Add environment variables from your `.env`
   - Deploy!

✅ **Free tier includes**: 1 free web service, auto-deploys on git push

---

## Option 2: **Railway.app** (Very Easy)

### Steps:
1. **Sign up** at https://railway.app
2. **Push to GitHub** (same as above)
3. **In Railway Dashboard**:
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Add environment variables (Database & OpenAI keys)
   - Railway auto-detects `requirements.txt` and deploys

✅ **Free tier**: $5/month free credits

---

## Option 3: **Fly.io** (More Control)

### Steps:
1. **Install Fly CLI**: https://fly.io/docs/getting-started/installing-flyctl/
2. **Sign up** at https://fly.io

3. **Create `Dockerfile`**:
   ```dockerfile
   FROM python:3.13.9-slim
   
   WORKDIR /app
   
   RUN apt-get update && apt-get install -y --no-install-recommends gcc
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   EXPOSE 8080
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```

4. **Create `fly.toml`**:
   ```toml
   app = "lab-chatbot-backend"
   primary_region = "sin"  # Singapore (or closest region)
   
   [env]
   API_HOST = "0.0.0.0"
   LLM_MODEL = "gpt-4o-mini"
   
   [[services]]
   internal_port = 8080
   processes = ["app"]
   
   [[services.ports]]
   port = 80
   handlers = ["http"]
   
   [[services.ports]]
   port = 443
   handlers = ["tls", "http"]
   ```

5. **Deploy**:
   ```powershell
   fly auth login
   fly deploy
   fly secrets set DB_HOST=your_db_host DB_USER=postgres DB_PASSWORD=your_pass OPENAI_API_KEY=your_key
   ```

✅ **Free tier**: 3 shared-cpu-1x 256MB VMs, 3GB persistent storage

---

## Option 4: **Heroku** (Legacy - Limited Free)

⚠️ **Note**: Heroku removed free tier in Nov 2022, but dynos start at $7/month

---

## Option 5: **PythonAnywhere** (Python-Specific)

### Steps:
1. **Sign up** at https://www.pythonanywhere.com (free tier available)
2. **Push code or upload via web interface**
3. **Set up web app**:
   - Files → Upload your project
   - Web → Add web app (FastAPI)
   - Reload app
   - Set environment variables in admin panel

---

## Quick Comparison

| Platform | Cost | Setup Time | Features |
|----------|------|-----------|----------|
| **Render.com** | Free | 5 min | Best free tier, auto-deploy |
| **Railway.app** | $5/mo credits | 5 min | Simple, generous free tier |
| **Fly.io** | Free tier | 10 min | More control, good scale |
| **PythonAnywhere** | Free | 10 min | Python-specific |

---

## ⚠️ Important Notes

### Database Access
Your `.env` has RDS database credentials - they should work from any cloud service. Ensure:
- RDS security group allows inbound from your deployment region
- Database user has proper permissions

### Environment Variables
Never commit `.env` to GitHub! Add to `.gitignore`:
```
.env
.env.local
*.pyc
__pycache__/
```

### API Keys
Your OpenAI API key is exposed in `.env.example` - consider:
1. Rotating the key immediately
2. Using secret management in deployment platform
3. Never commit real keys to git

---

## Deployment Checklist

- [ ] Push code to GitHub (without `.env`)
- [ ] Choose hosting platform
- [ ] Add environment variables securely
- [ ] Test `/docs` endpoint after deployment
- [ ] Monitor logs for errors
- [ ] Set up monitoring/alerts

---

## Next Steps

1. **Choose Render.com or Railway.app** for easiest setup
2. **Create GitHub repo** with your code
3. **Add `render.yaml` or connect repo** to your chosen platform
4. **Set environment variables** in platform dashboard
5. **Deploy** and get your live URL!

Your backend will be live at: `https://your-app-name.onrender.com` (or similar)
