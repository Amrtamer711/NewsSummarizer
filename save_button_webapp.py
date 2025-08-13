# Alternative save button implementation for web app

def create_webapp_save_button(title, url, section, desc):
    """Create save button that connects to local web app"""
    # Replace with your actual server URL
    SERVER_URL = "http://localhost:5000"  # or your deployed URL
    
    save_url = f"{SERVER_URL}/save?"
    save_url += f"title={quote(title)}"
    save_url += f"&url={quote(url)}"
    save_url += f"&section={quote(section)}"
    save_url += f"&summary={quote(desc)}"
    
    return f'<a href="{save_url}" target="_blank" style="float:right;background:#4CAF50;color:white;padding:4px 8px;border-radius:4px;text-decoration:none;font-size:12px;margin-left:10px;">Save 📌</a>'