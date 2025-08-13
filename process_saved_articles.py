import imaplib
import email
from email.header import decode_header
import sqlite3
from datetime import datetime
import re
from config import APP_PSWD

# Email configuration
SAVE_EMAIL = "save.multiply.news@gmail.com"
IMAP_SERVER = "imap.gmail.com"

def setup_database():
    """Create SQLite database for saved articles"""
    conn = sqlite3.connect('saved_articles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            section TEXT,
            saved_date TEXT,
            processed_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

def parse_save_email(msg):
    """Extract article info from save email"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = msg.get_payload(decode=True).decode()
    
    # Parse the structured body
    article_data = {}
    patterns = {
        'title': r'Article: (.+?)(?:\n|$)',
        'summary': r'Summary: (.+?)(?:\n\n|$)',
        'url': r'URL: (.+?)(?:\n|$)',
        'section': r'Section: (.+?)(?:\n|$)',
        'saved_date': r'Saved on: (.+?)(?:\n|$)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, body, re.DOTALL)
        if match:
            article_data[key] = match.group(1).strip()
    
    return article_data

def process_saved_emails():
    """Check for new save emails and store them"""
    conn = setup_database()
    cursor = conn.cursor()
    
    # Connect to email
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(SAVE_EMAIL, APP_PSWD)
    mail.select('inbox')
    
    # Search for unread emails with "Save:" in subject
    status, messages = mail.search(None, 'UNSEEN SUBJECT "Save:"')
    
    if status == "OK":
        for num in messages[0].split():
            status, msg_data = mail.fetch(num, '(RFC822)')
            
            if status == "OK":
                msg = email.message_from_bytes(msg_data[0][1])
                article_data = parse_save_email(msg)
                
                if article_data.get('title'):
                    # Save to database
                    cursor.execute('''
                        INSERT INTO saved_articles (title, summary, url, section, saved_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        article_data.get('title', ''),
                        article_data.get('summary', ''),
                        article_data.get('url', ''),
                        article_data.get('section', ''),
                        article_data.get('saved_date', '')
                    ))
                    
                    print(f"✅ Saved: {article_data['title']}")
                
                # Mark as read
                mail.store(num, '+FLAGS', '\\Seen')
    
    conn.commit()
    conn.close()
    mail.logout()

def get_saved_articles(days=30):
    """Retrieve recent saved articles"""
    conn = sqlite3.connect('saved_articles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM saved_articles 
        WHERE datetime(processed_date) >= datetime('now', '-' || ? || ' days')
        ORDER BY processed_date DESC
    ''', (days,))
    
    articles = cursor.fetchall()
    conn.close()
    
    return articles

if __name__ == "__main__":
    print("🔍 Processing saved article emails...")
    process_saved_emails()
    
    print("\n📌 Recent saved articles:")
    saved = get_saved_articles()
    for article in saved:
        print(f"\n- {article[1]}")  # title
        print(f"  Section: {article[4]}")
        print(f"  Saved: {article[5]}")