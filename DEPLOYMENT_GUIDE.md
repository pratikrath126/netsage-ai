# 🚀 NetSage AI — Vercel Deployment Guide

You can deploy NetSage AI to Vercel in under 2 minutes using either **GitHub** (recommended) or the **Vercel CLI**.

---

## Method 1: Deploy via GitHub (Easiest)

### Step 1: Push project to GitHub
In your project directory (`c:\Users\prati\OneDrive\Documents\netcad`):
```bash
git init
git add .
git commit -m "NetSage AI Project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

### Step 2: Import into Vercel
1. Go to [vercel.com](https://vercel.com) and log in.
2. Click **"Add New..."** → **"Project"**.
3. Select your GitHub repository and click **Import**.

### Step 3: Add Environment Variables in Vercel
Before clicking Deploy, expand the **Environment Variables** section and add:
* `OPENROUTER_API_KEY`: `your-openrouter-key`
* `MODEL`: `deepseek/deepseek-v4-flash-0731`

### Step 4: Click Deploy! 🎉
Vercel will build the Python environment and give you a live production URL (e.g., `https://netsage-ai.vercel.app`).

---

## Method 2: Deploy via Vercel CLI (Direct from Terminal)

If you have Node.js / Vercel CLI installed:

```bash
# 1. Install Vercel CLI (if not installed)
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy
vercel --prod
```

When prompted:
* Set up and deploy? **Yes**
* Which scope? Select your personal account
* Link to existing project? **No**
* What's your project's name? `netsage-ai`
* In which directory is your code located? `./`

Add your environment variables either in the Vercel Dashboard settings or by running:
```bash
vercel env add OPENROUTER_API_KEY production
vercel env add MODEL production
```

---

## ⚙️ Configuration Files Already Included

* **`vercel.json`**: Configures the `@vercel/python` builder and routes all web traffic to `app.py`.
* **`requirements.txt`**: Specifies `flask`, `openai`, `python-dotenv`.
* **`.vercelignore`**: Prevents secrets and temporary files from being uploaded.
