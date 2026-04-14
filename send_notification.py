import os
from twilio.rest import Client

# 1. Configuration (Read from secure environment variables)
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')

def format_wa(number):
    return f"whatsapp:{number}" if number and not number.startswith("whatsapp:") else number

from_number = format_wa(os.getenv('TWILIO_FROM_NUMBER', 'whatsapp:+14155238886'))
to_number = format_wa(os.getenv('TWILIO_TO_NUMBER'))

# URL to the PDF hosted in this public GitHub repository
pdf_repo_url = "https://raw.githubusercontent.com/Shilpanshu/Whatsapp_notification/main/dummy_report.pdf"
pdf_url = os.getenv('PDF_URL', pdf_repo_url)

if not all([account_sid, auth_token, to_number]):
    print("Error: Required environment variables are missing.")
    print("Ensure you have set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_TO_NUMBER.")
    exit(1)

client = Client(account_sid, auth_token)

# 2. Execution
try:
    message = client.messages.create(
        from_=from_number,
        body="Automated Update: Here is your scheduled Daily Report PDF test.",
        media_url=[pdf_url],
        to=to_number
    )
    print(f"Message sent successfully! SID: {message.sid}")
except Exception as e:
    print(f"Failed to send message: {e}")
    exit(1)
