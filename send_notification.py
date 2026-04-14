import os
import sys
import time
import requests
from twilio.rest import Client

# ---------------------------------------------------------
# 1. Configuration (Loaded from Secure Environment Variables)
# ---------------------------------------------------------
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
content_sid = os.getenv('TWILIO_CONTENT_SID')  # The official Template SID (To bypass 24hr block)

def format_wa(number):
    return f"whatsapp:{number}" if number and not number.startswith("whatsapp:") else number

from_number = format_wa(os.getenv('TWILIO_FROM_NUMBER', 'whatsapp:+14155238886'))
to_number = format_wa(os.getenv('TWILIO_TO_NUMBER'))
pdf_repo_url = os.getenv('PDF_URL', "https://raw.githubusercontent.com/Shilpanshu/Whatsapp_notification/main/dummy_report.pdf")

if not all([account_sid, auth_token, to_number]):
    print("ERROR: Account SID, Auth Token, and To Number are required.")
    sys.exit(1)

# ---------------------------------------------------------
# 2. FAIL-SAFE 1: URL Validation (The "URL Check")
# ---------------------------------------------------------
print(f"[Health Check] Validating PDF availability at: {pdf_repo_url}")
try:
    # Use timeout to prevent hanging forever
    response = requests.head(pdf_repo_url, allow_redirects=True, timeout=10)
    if response.status_code == 405: # Fallback if HEAD is blocked
        response = requests.get(pdf_repo_url, stream=True, timeout=10)
    
    if response.status_code >= 400:
        print(f"CRITICAL ERROR: PDF URL returned HTTP {response.status_code}. Halting operation to prevent broken message.")
        sys.exit(1)
    print("[Health Check] Passed. PDF is accessible.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to connect to the PDF URL. Network or invalid link: {e}")
    sys.exit(1)

# ---------------------------------------------------------
# 3. FAIL-SAFE 2: Twilio API Execution with Retry Logic
# ---------------------------------------------------------
client = Client(account_sid, auth_token)

MAX_RETRIES = 3
RETRY_DELAY = 120  # 2 minutes

for attempt in range(1, MAX_RETRIES + 1):
    try:
        print(f"Attempt {attempt}/{MAX_RETRIES} to deliver message...")
        
        # Prepare the payload
        msg_kwargs = {
            "from_": from_number,
            "to": to_number
        }
        
        if content_sid:
            # ENTERPRISE MODE: Using an approved Twilio Content Template SID
            msg_kwargs["content_sid"] = content_sid
            # Note: For media templates, Twilio usually requires you to inject the URL as a variable or it's hardcoded in the template.
            # Check Twilio documentation on Content Variables if your template requires dynamic URL injection.
        else:
            # FALLBACK/TEST MODE: Standard Session message
            msg_kwargs["body"] = "Automated Update: Here is your scheduled Daily Report PDF."
            msg_kwargs["media_url"] = [pdf_repo_url]
            
        message = client.messages.create(**msg_kwargs)
        
        print(f"SUCCESS: Message delivered! SID: {message.sid}")
        break # Exit loop successfully
        
    except Exception as e:
        print(f"WARN: Twilio API Error encountered: {e}")
        if attempt < MAX_RETRIES:
            print(f"Recovering: Sleeping for {RETRY_DELAY} seconds before retrying...")
            time.sleep(RETRY_DELAY)
        else:
            # ---------------------------------------------------------
            # 4. FAIL-SAFE 3: The Native Alert System
            # ---------------------------------------------------------
            print("CRITICAL ERROR: All 3 Twilio delivery attempts failed.")
            print("Triggering GitHub Action Failure to dispatch native Email Alert to repository owner.")
            sys.exit(1)
