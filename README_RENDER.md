# NewsAI Daily Email - Render Deployment Guide

This guide will help you deploy the NewsAI Daily Email service on Render for automatic daily execution at 6 AM.

## Prerequisites

1. A Render account (sign up at https://render.com)
2. All required API keys:
   - Gmail App Password
   - NewsAPI Key
   - NewsData.io Key
   - Perplexity API Key
   - OpenAI API Key
   - Google Gemini API Key

## Deployment Steps

### 1. Create a New Cron Job on Render

1. Log in to your Render dashboard
2. Click "New +" and select "Cron Job"
3. Connect your GitHub repository containing this code

### 2. Configure the Cron Job

1. **Name**: `newsai-daily-email`
2. **Environment**: `Python 3`
3. **Build Command**: `pip install -r requirements.txt`
4. **Command**: `python send_email_render.py`
5. **Schedule**: `0 6 * * *` (6:00 AM UTC daily)
   - Adjust for your timezone if needed
   - Use https://crontab.guru/ to customize

### 3. Set Environment Variables

In the Render dashboard, add the following environment variables:

#### Required (Secret):
- `APP_PSWD` - Your Gmail app password
- `NEWS_API_KEY` - Your NewsAPI key
- `NEWS_IO_KEY` - Your NewsData.io key
- `PERPLEXITY_API_KEY` - Your Perplexity API key
- `OPENAI_API_KEY` - Your OpenAI API key
- `GEMINI_API_KEY` - Your Google Gemini API key

#### Optional Configuration:
- `FROM_EMAIL` - Sender email (default: daily.multiply.news@gmail.com)
- `TO_EMAIL` - Recipient email (default: atmh2002@gmail.com)
- `OPENAI_MODEL` - OpenAI model to use (default: gpt-5)
- `PERPLEXITY_MODEL` - Perplexity model to use (default: sonar-pro)
- `GEMINI_MODEL` - Gemini model to use (default: gemini-2.5-pro)
- `ENABLE_OPENAI` - Enable OpenAI (default: true)
- `ENABLE_PERPLEXITY` - Enable Perplexity (default: true)
- `ENABLE_GEMINI` - Enable Gemini (default: true)
- `TEST_MODE` - Run in test mode (default: false)

### 4. Deploy

1. Click "Create Cron Job"
2. Render will build and deploy your service
3. The cron job will run automatically at the scheduled time

## Testing

### Manual Test Run
In the Render dashboard, you can manually trigger the cron job:
1. Go to your cron job service
2. Click "Manual Run"
3. Check the logs to see the output

### Test Mode
Set `TEST_MODE=true` in environment variables to:
- Always fetch stock data (regardless of day)
- Show additional debug information

## Monitoring

1. **Logs**: View in Render dashboard under your service
2. **Email**: Check if emails are being received at scheduled time
3. **Alerts**: Set up Render alerts for job failures

## Timezone Adjustment

Render uses UTC time. To run at 6 AM in your local timezone:

- **UAE (UTC+4)**: Use `0 2 * * *` (2:00 AM UTC = 6:00 AM UAE)
- **EST (UTC-5)**: Use `0 11 * * *` (11:00 AM UTC = 6:00 AM EST)
- **PST (UTC-8)**: Use `0 14 * * *` (2:00 PM UTC = 6:00 AM PST)

## Troubleshooting

1. **Email not sending**: Check APP_PSWD is correct and Gmail allows app passwords
2. **API errors**: Verify all API keys are correctly set
3. **No stock data**: Check if it's Monday (or enable TEST_MODE)
4. **Missing images**: Matplotlib backend is set to 'Agg' for server environments

## Cost

- Render Free Plan: 750 hours/month of cron job runtime
- This job runs once daily (~5 minutes) = ~150 minutes/month
- Well within free tier limits

## Security Notes

- All API keys are stored as encrypted environment variables
- Never commit API keys to the repository
- Use .env.example as a template for local development