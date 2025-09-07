import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Sequence
from config import OUTLOOK_SMTP_HOST, OUTLOOK_SMTP_PORT, OUTLOOK_SMTP_USER, OUTLOOK_SMTP_PASS


def send_outlook_email(subject: str, html_body: str, to_addrs: Sequence[str]) -> None:
	msg = MIMEMultipart()
	msg["From"] = OUTLOOK_SMTP_USER
	msg["To"] = ", ".join(to_addrs)
	msg["Subject"] = subject
	msg.attach(MIMEText(html_body, "html"))
	with smtplib.SMTP(OUTLOOK_SMTP_HOST, OUTLOOK_SMTP_PORT) as server:
		server.ehlo()
		server.starttls()
		server.login(OUTLOOK_SMTP_USER, OUTLOOK_SMTP_PASS)
		server.sendmail(OUTLOOK_SMTP_USER, list(to_addrs), msg.as_string()) 