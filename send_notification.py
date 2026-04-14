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
content_sid = os.getenv('TWILIO_CONTENT_SID')  # The official Template SID

def format_wa(number):
    number = number.strip()
    return f"whatsapp:{number}" if number and not number.startswith("whatsapp:") else number

from_number = format_wa(os.getenv('TWILIO_FROM_NUMBER', 'whatsapp:+14155238886'))

# Parse comma-separated list of multiple recipients, with a fallback to the old single variable
raw_to_numbers = os.getenv('TWILIO_TO_NUMBERS', os.getenv('TWILIO_TO_NUMBER'))
to_numbers = [format_wa(n) for n in raw_to_numbers.split(',')] if raw_to_numbers else []

# The static URL mapped to your cloud folder where you dynamically replace the PDF file
pdf_repo_url = os.getenv('PDF_URL', "https://raw.githubusercontent.com/Shilpanshu/Whatsapp_notification/main/dummy_report.pdf")

if not all([account_sid, auth_token]) or not to_numbers:
    print("ERROR: Account SID, Auth Token, and To Number(s) are required.")
    sys.exit(1)

# ---------------------------------------------------------
# 2. FAIL-SAFE 1: URL Validation (The "URL Check")
# ---------------------------------------------------------
print(f"[Health Check] Validating dynamic PDF availability at: {pdf_repo_url}")
try:
    response = requests.head(pdf_repo_url, allow_redirects=True, timeout=10)
    if response.status_code == 405: # Fallback if HEAD is blocked
        response = requests.get(pdf_repo_url, stream=True, timeout=10)
    
    if response.status_code >= 400:
        print(f"CRITICAL ERROR: PDF URL returned HTTP {response.status_code}. Halting operation.")
        sys.exit(1)
    print("[Health Check] Passed. PDF is fully accessible online.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to connect to the PDF URL: {e}")
    sys.exit(1)

# ---------------------------------------------------------
# 3. FAIL-SAFE 2: Twilio Broadcast with Retry Logic
# ---------------------------------------------------------
client = Client(account_sid, auth_token)
MAX_RETRIES = 3
RETRY_DELAY = 120  # 2 minutes

failures = 0

print(f"Starting broadcast to {len(to_numbers)} recipient(s)...")

for subscriber in to_numbers:
    print(f"\n--- Attemping delivery to {subscriber} ---")
    subscriber_success = False
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg_kwargs = {
                "from_": from_number,
                "to": subscriber
            }
            
            if content_sid:
                # ENTERPRISE MODE: Using Template SID to bypass 24hr block
                msg_kwargs["content_sid"] = content_sid
            else:
                # FALLBACK MODE: Session message
                msg_kwargs["body"] = "Automated Update: Here is the latest version of your scheduled PDF."
                msg_kwargs["media_url"] = [pdf_repo_url]
                
            message = client.messages.create(**msg_kwargs)
            print(f"SUCCESS: Delivered! SID: {message.sid}")
            subscriber_success = True
            break
            
        except Exception as e:
            print(f"WARN: Twilio Error for {subscriber}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Recovering: Sleeping for {RETRY_DELAY}s before retrying this message...")
                time.sleep(RETRY_DELAY)
    
    if not subscriber_success:
        print(f"ERROR: Failed to deliver to {subscriber} after {MAX_RETRIES} attempts.")
        failures += 1

# ---------------------------------------------------------
# 4. FAIL-SAFE 3: The Native Alert System
# ---------------------------------------------------------
if failures > 0:
    print(f"\nCRITICAL ERROR: Failed to deliver to {failures} out of {len(to_numbers)} recipients.")
    print("Triggering GitHub Action Failure to dispatch native Email Alert to repository owner.")
    sys.exit(1)

print("\nAll messages delivered successfully to all recipients!")
