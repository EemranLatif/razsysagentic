import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
message = Mail(
from_email="imranlatifclouds@gmail.com",
to_emails="imranlatifclouds@gmail.com",
subject="SendGrid test",
html_content="<strong>It works!</strong>")
sg = SendGridAPIClient(os.environ.get("sendgrid_api_key"))
response = sg.send(message)
print(response.status_code) # 202 = accepted

