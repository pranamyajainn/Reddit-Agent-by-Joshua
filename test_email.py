import smtplib
import os
from email.message import EmailMessage

sender = os.environ.get("GMAIL_ADDRESS", "joshua.us333@gmail.com")
app_password = os.environ.get("GMAIL_APP_PASSWORD", "wfnd mrpo dnzn zggw")

msg = EmailMessage()
msg["Subject"] = "Test SMTP"
msg["From"] = sender
msg["To"] = "pranamyajeet@gmail.com"
msg.set_content("Test")

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        # Some systems need ehlo
        smtp.ehlo()
        smtp.login(sender, app_password.replace(" ", ""))
        smtp.send_message(msg)
    print("Success")
except Exception as e:
    print("Error:", e)
