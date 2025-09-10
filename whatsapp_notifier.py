import os
from twilio.rest import Client
from config import BASE_PUBLIC_URL

def send_whatsapp_digest(digest_data, is_monday=False):
    """Send WhatsApp notification with digest summary and link"""
    
    # Get Twilio credentials from environment
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_whatsapp = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
    to_whatsapp = os.environ.get('BOSS_WHATSAPP_NUMBER', 'whatsapp:+971504863342')
    
    # Debug logging
    print(f"🔍 WhatsApp Debug:")
    print(f"   - Account SID: {'SET' if account_sid else 'NOT SET'}")
    print(f"   - Auth Token: {'SET' if auth_token else 'NOT SET'}")
    print(f"   - From: {from_whatsapp}")
    print(f"   - To: {to_whatsapp}")
    print(f"   - BASE_PUBLIC_URL: {BASE_PUBLIC_URL}")
    
    if not account_sid or not auth_token:
        print("⚠️ Twilio credentials not configured, skipping WhatsApp notification")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        date_str = digest_data['date']
        
        # Build message summary
        total_articles = sum(len(articles) for articles in digest_data['sections'].values())
        
        # Create simple message
        if is_monday:
            message = f"📊 *Weekly Digest Ready!*\n\n"
            message += f"Your weekly stocks + news digest for {date_str} is ready!\n"
            message += f"Total articles: {total_articles}\n\n"
            message += f"📰 View digest: {BASE_PUBLIC_URL}/\n"
            message += f"📊 View stocks: {BASE_PUBLIC_URL}/stocks"
        else:
            message = f"📰 *Daily Digest Ready!*\n\n"
            message += f"Your daily news digest for {date_str} is ready!\n"
            message += f"Total articles: {total_articles}\n\n"
            message += f"📰 View digest: {BASE_PUBLIC_URL}/"
        
        # Send WhatsApp message
        result = client.messages.create(
            from_=from_whatsapp,
            body=message,
            to=to_whatsapp
        )
        
        print(f"✅ WhatsApp notification sent: {result.sid}")
        return True
            
    except Exception as e:
        print(f"❌ WhatsApp notification failed: {e}")
        return False

def send_test_whatsapp():
    """Send a test WhatsApp message to verify setup"""
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_whatsapp = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
    to_whatsapp = os.environ.get('BOSS_WHATSAPP_NUMBER', 'whatsapp:+971504863342')
    
    if not account_sid or not auth_token:
        print("❌ Twilio credentials not configured!")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_whatsapp,
            body="✅ NewsAI WhatsApp integration is working!\n\nYou'll receive daily digest notifications here.",
            to=to_whatsapp
        )
        print(f"✅ Test message sent: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Test message failed: {e}")
        return False

if __name__ == "__main__":
    # Test the WhatsApp setup
    send_test_whatsapp()