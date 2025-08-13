from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime
from urllib.parse import unquote

app = Flask(__name__)

# Simple HTML template for confirmation
SAVE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Article Saved</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 600px; 
            margin: 50px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .success { 
            background: #4CAF50; 
            color: white; 
            padding: 15px; 
            border-radius: 5px; 
            margin-bottom: 20px;
        }
        button {
            background: #333;
            color: white;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="success">✅ Article saved successfully!</div>
    <h2>{{ title }}</h2>
    <p>{{ summary }}</p>
    <button onclick="window.close()">Close Window</button>
</body>
</html>
'''

def init_db():
    conn = sqlite3.connect('saved_articles.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            section TEXT,
            saved_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/save')
def save_article():
    # Get parameters from URL
    title = unquote(request.args.get('title', ''))
    url = unquote(request.args.get('url', ''))
    section = unquote(request.args.get('section', ''))
    summary = unquote(request.args.get('summary', ''))
    
    # Save to database
    conn = sqlite3.connect('saved_articles.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO saved_articles (title, summary, url, section)
        VALUES (?, ?, ?, ?)
    ''', (title, summary, url, section))
    conn.commit()
    conn.close()
    
    # Return success page
    return render_template_string(SAVE_TEMPLATE, title=title, summary=summary)

@app.route('/saved')
def view_saved():
    # Simple view of all saved articles
    conn = sqlite3.connect('saved_articles.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM saved_articles ORDER BY saved_date DESC')
    articles = cursor.fetchall()
    conn.close()
    
    html = '<h1>Saved Articles</h1><ul>'
    for article in articles:
        html += f'<li><a href="{article[3]}">{article[1]}</a> - {article[4]}</li>'
    html += '</ul>'
    
    return html

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)