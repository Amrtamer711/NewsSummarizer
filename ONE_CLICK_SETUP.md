# One-Click Save Setup Guide

This creates a truly one-click save system - your CEO clicks once, article is saved, window closes automatically.

## Step 1: Create Google Sheet
1. Go to [Google Sheets](https://sheets.google.com)
2. Create new spreadsheet named "Saved Articles"
3. Copy the ID from the URL: `https://docs.google.com/spreadsheets/d/[THIS_IS_THE_ID]/edit`

## Step 2: Create Google Apps Script
1. Go to [Google Apps Script](https://script.google.com)
2. Create new project
3. Delete default code
4. Paste contents of `google_apps_script.gs`
5. Replace `YOUR_SPREADSHEET_ID` with your sheet ID from Step 1

## Step 3: Deploy the Script
1. Click "Deploy" → "New Deployment"
2. Settings:
   - Type: Web app
   - Execute as: Me (your account)
   - Who has access: Anyone
3. Click "Deploy"
4. Copy the Web app URL (looks like: `https://script.google.com/macros/s/AKfyc.../exec`)

## Step 4: Update send_email.py
Replace `YOUR_SCRIPT_ID` in send_email.py with your script ID from the URL

## How it Works:
1. CEO sees "Save 📌" button next to articles
2. One click opens small window
3. Article automatically saves to Google Sheet
4. Window shows "✅ Article Saved!" 
5. Window auto-closes after 2 seconds

## Benefits:
- **One click** - no forms, no typing
- **Automatic** - saves directly to spreadsheet
- **Fast** - window closes itself
- **Clean** - no email clutter
- **Organized** - all saves in one Google Sheet

## Testing:
1. Run your email script in test mode
2. Click a Save button
3. Check your Google Sheet - article should appear
4. Window should close automatically

That's it! True one-click saving with zero friction.