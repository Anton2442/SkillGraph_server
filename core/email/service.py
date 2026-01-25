import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os
from dotenv import load_dotenv


load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
BASE_URL = os.getenv("SERVER_BASE_URL")


class EmailService:

    @staticmethod
    def send_verification_email(email: str, token: str):
        verify_link = f"{BASE_URL}/auth/verify-email?token={token}"

        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg["Subject"] = "SkillGraph подтвердите почту"

        body = f"""
        <h2>SkillGraph подтверждение почты</h2>
        <p>Чтобы подтвердить почту перейдите по ссылке:</p>
        <a href="{verify_link}">{verify_link}</a>
        """

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)