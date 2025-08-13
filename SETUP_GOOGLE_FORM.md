# Setting Up Google Form for Article Saving

## Step 1: Create the Form
1. Go to [Google Forms](https://forms.google.com)
2. Create a new blank form
3. Title it "Saved Articles" or similar

## Step 2: Add Fields
Add these fields in order:
1. **Title** (Short answer) - Required
2. **URL** (Short answer) - Required  
3. **Section** (Short answer) - Required
4. **Summary** (Paragraph) - Optional

## Step 3: Get Pre-filled Link
1. Click the 3 dots menu → "Get pre-filled link"
2. Fill in test data:
   - Title: TEST_TITLE
   - URL: TEST_URL
   - Section: TEST_SECTION
   - Summary: TEST_SUMMARY
3. Click "Get link" and copy it

## Step 4: Extract IDs
Your link will look like:
```
https://docs.google.com/forms/d/e/1FAIpQLSd.../viewform?usp=pp_url&entry.1234567890=TEST_TITLE&entry.0987654321=TEST_URL...
```

Extract:
- Form ID: `1FAIpQLSd...` (between /e/ and /viewform)
- Title field ID: The number after `entry.` for TEST_TITLE
- URL field ID: The number after `entry.` for TEST_URL
- Section field ID: The number after `entry.` for TEST_SECTION
- Summary field ID: The number after `entry.` for TEST_SUMMARY

## Step 5: Update send_email.py
Replace in the code:
- `YOUR_GOOGLE_FORM_ID` with your Form ID
- `entry.1234567890` with your actual Title field ID
- `entry.0987654321` with your actual URL field ID
- `entry.1122334455` with your actual Section field ID
- `entry.5544332211` with your actual Summary field ID

## Step 6: Set up Responses
1. In your form, go to "Responses" tab
2. Click the Google Sheets icon to create a spreadsheet
3. This will automatically collect all saved articles

## Benefits:
- One click to save (opens in new tab)
- Pre-filled with all article data
- CEO just needs to click "Submit"
- All saves go to a Google Sheet automatically
- Can add notes/tags before submitting
- Works on all devices
- No email clutter