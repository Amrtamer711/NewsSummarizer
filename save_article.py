import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from urllib.parse import quote

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # You'll need to set this up
SPREADSHEET_ID = 'your_spreadsheet_id_here'  # Create a sheet and add ID here

def setup_sheets_service():
    """Initialize Google Sheets API service"""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def save_article_to_sheet(article_data):
    """Save an article to Google Sheets"""
    service = setup_sheets_service()
    
    # Prepare row data
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
        article_data.get('title', ''),
        article_data.get('summary', ''),
        article_data.get('source', ''),
        article_data.get('url', ''),
        article_data.get('section', ''),
        article_data.get('notes', '')  # CEO's notes
    ]
    
    # Append to sheet
    body = {'values': [row]}
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='A:G',  # Adjust based on your columns
        valueInputOption='RAW',
        body=body
    ).execute()
    
    return result

def generate_save_link(article, section):
    """Generate a save link for an article"""
    # Create a simple web endpoint or use a URL shortener
    # This is a placeholder - you'd implement the actual endpoint
    data = {
        'title': article['title'],
        'summary': article['summary'],
        'source': article['source'],
        'url': article['url'],
        'section': section
    }
    
    # Encode the data for URL
    encoded = quote(json.dumps(data))
    save_url = f"https://your-domain.com/save?data={encoded}"
    
    # Or use a simpler approach with just the article URL
    # save_url = f"https://your-domain.com/save?url={quote(article['url'])}&section={quote(section)}"
    
    return save_url

# Example usage in your email HTML generation
def format_article_with_save_button(article, section):
    """Format article HTML with save button"""
    save_link = generate_save_link(article, section)
    
    return f"""
    <li style='margin-bottom:15px;'>
        <a href='{article["url"]}' style='color:#4fc3f7;font-weight:bold;text-decoration:none;font-size:16px;'>
            {article["title"]}
        </a>
        <a href='{save_link}' style='float:right;color:#4CAF50;text-decoration:none;font-size:14px;'>
            [Save 📌]
        </a>
        <p style='margin:4px 0 10px 0;color:#ccc;font-size:14px;'>{article["summary"]}</p>
    </li>
    """