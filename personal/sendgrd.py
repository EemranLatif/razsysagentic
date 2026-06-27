import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
	from_email="imranlatifclouds@gmail.com",
	to_emails="imranlatifclouds@gmail.com",
	subject="SendGrid test",
	html_content="<strong>It works!</strong>"
)

# Prefer canonical env var name but accept lowercase for compatibility
sendgrid_key = os.environ.get("SENDGRID_API_KEY") or os.environ.get("sendgrid_api_key")

if not sendgrid_key:
	print("SendGrid API key not found in environment. Please set SENDGRID_API_KEY.")
else:
	print("SendGrid key found (first 8 chars):", sendgrid_key[:8])
	sg = SendGridAPIClient(sendgrid_key)
	print("SendGrid client initialized:", sg)
	try:
		response = sg.send(message)
		print("Status code:", response.status_code)  # 202 = accepted
		# optional: print body/headers for debugging
		if hasattr(response, "body"):
			print("Response body:", response.body)
		if hasattr(response, "headers"):
			print("Response headers:", response.headers)
	except Exception as e:
		# Catch and print details instead of letting the notebook error out
		print("Error sending email:", type(e).__name__, e)
		# Provide guidance for common 403 reasons
		# Some SendGrid SDK exceptions expose status_code/body attributes
		status = getattr(e, "status_code", None)
		body = getattr(e, "body", None)
		if status:
			print("Status code from exception:", status)
		if body:
			print("Error body from exception:", body)
		if status == 403:
			print("403 Forbidden: check that the API key is correct, has Mail Send permission, and that the sender email is verified in your SendGrid account.")