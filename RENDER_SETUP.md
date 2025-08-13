# Quick Render Setup Guide for NewsAI

Since you already have a `.env` file with all your API keys, here's the simple setup:

## 1. First, test locally to make sure everything works:
```bash
cd /Users/amr/Documents/NewsAI
source venv/bin/activate
python send_email.py
```

## 2. Create a GitHub repository:
```bash
git init
git add .
git commit -m "Initial commit for NewsAI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/newsai.git
git push -u origin main
```

## 3. On Render.com:

1. **Sign up/Login** at https://render.com

2. **Create New Cron Job**:
   - Click "New +" → "Cron Job"
   - Connect your GitHub account
   - Select your NewsAI repository

3. **Configure the Cron Job**:
   - **Name**: `newsai-daily-email`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Command**: `python send_email.py`
   - **Schedule**: `0 2 * * *` (6 AM UAE time)

4. **Add Environment Variables** (copy from your .env file):
   - Click "Environment" tab
   - Add each variable:
     - `APP_PSWD` → (your gmail app password)
     - `NEWS_API_KEY` → (your newsapi key)
     - `NEWS_IO_KEY` → (your newsdata key)
     - `OPENAI_API_KEY` → (your openai key)
     - `PERPLEXITY_API_KEY` → (your perplexity key)
     - `GOOGLE_API_KEY` → (your google/gemini key)

5. **Deploy**:
   - Click "Create Cron Job"
   - Wait for the build to complete

## 4. Test the deployment:
- In Render dashboard, click "Manual Run" to test
- Check the logs to see if it worked

## That's it! 

Your CEO will now receive the email every day at 6 AM UAE time automatically.

## Notes:
- The free tier gives you 750 hours/month (more than enough)
- Render will automatically restart if it crashes
- You can view logs anytime in the dashboard
- To update, just push changes to GitHub