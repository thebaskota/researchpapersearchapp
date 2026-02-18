# Research Paper & Expert Finder - Deployment Guide

## Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

Opens at: `http://localhost:8501`

---

## Deploy to Render (Live in 5 minutes)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `paper-finder` (or any name)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
   - **Instance Type:** `Free`

5. Click **"Create Web Service"**

Wait 5-10 minutes for deployment. You'll get a URL like:
`https://paper-finder.onrender.com`

---

## Alternative: Deploy to Streamlit Cloud (Even Easier)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click **"New app"**
5. Select your repo, branch, and `app.py`
6. Click **"Deploy"**

Done! Your app will be live at: `https://YOUR-APP-NAME.streamlit.app`

---

## Notes

- The `out_main/chroma` directory must be included in your repo for the app to work
- First load will be slow (downloading ML models)
- Free tier may sleep after inactivity (30s wake-up time)
