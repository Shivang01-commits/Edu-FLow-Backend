"""
email_service.py
----------------
Sends emails via Gmail SMTP.

Required .env variables:
  GMAIL_SENDER_EMAIL=yourapp@gmail.com
  GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   ← Gmail App Password (not your Gmail login password)
  APP_NAME=Padhai App
  APP_URL=https://yourapp.com

How to get Gmail App Password:
  1. Go to Google Account → Security
  2. Enable 2-Step Verification
  3. Go to App Passwords → create one for "Mail"
  4. Use that 16-character password in GMAIL_APP_PASSWORD
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import HTTPException, status

GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
APP_NAME = os.getenv("APP_NAME", "Padhai App")
APP_URL = os.getenv("APP_URL", "https://yourapp.com")


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Core SMTP send function.
    All other functions in this file call this.
    """
    if not GMAIL_SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service not configured. Set GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD in .env",
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{APP_NAME} <{GMAIL_SENDER_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER_EMAIL, to_email, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gmail authentication failed. Check GMAIL_APP_PASSWORD in .env",
        )
    except smtplib.SMTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}",
        )


# Welcome email for new student
def send_student_welcome_email(
    to_email: str,
    first_name: str,
    school_name: str,
    password: str,
    grade_level: int,
    section: str,  # ← add this
) -> None:
    subject = f"Welcome to {APP_NAME} — Your Login Details"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 30px;">
      <div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color: #4F46E5;">Welcome to {APP_NAME}! 🎓</h2>

        <p>Hi <strong>{first_name}</strong>,</p>

        <p>You have been registered as a student at <strong>{school_name}</strong>.</p>
        <p>Your class: <strong>Class {grade_level} — Section {section.upper()}</strong></p>

        <div style="background: #F3F4F6; border-radius: 8px; padding: 20px; margin: 24px 0;">
          <p style="margin: 0 0 8px 0; color: #6B7280; font-size: 14px;">YOUR LOGIN DETAILS</p>
          <p style="margin: 4px 0;"><strong>Email:</strong> {to_email}</p>
          <p style="margin: 4px 0;"><strong>Password:</strong> <span style="font-family: monospace; font-size: 16px; color: #4F46E5;">{password}</span></p>
        </div>

        <p style="color: #EF4444; font-size: 14px;">
          ⚠️ Please change your password after your first login for security.
        </p>

        <a href="{APP_URL}/login"
           style="display: inline-block; background: #4F46E5; color: white; padding: 12px 28px;
                  border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 16px;">
          Login to {APP_NAME}
        </a>

        <hr style="margin: 32px 0; border: none; border-top: 1px solid #E5E7EB;">
        <p style="color: #9CA3AF; font-size: 12px;">
          If you did not expect this email, please contact your school administrator.<br>
          &copy; {APP_NAME}
        </p>

      </div>
    </body>
    </html>
    """
    _send_email(to_email, subject, html_body)


# Welcome email for new teacher
def send_teacher_welcome_email(
    to_email: str,
    first_name: str,
    school_name: str,
    password: str,
) -> None:
    subject = f"Welcome to {APP_NAME} — Teacher Account Created"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 30px;">
      <div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color: #059669;">Welcome to {APP_NAME}! 👨‍🏫</h2>

        <p>Hi <strong>{first_name}</strong>,</p>

        <p>Your teacher account has been created at <strong>{school_name}</strong>.</p>
        <p>You can manage your assigned classes and publish chapter content for your students.</p>

        <div style="background: #F3F4F6; border-radius: 8px; padding: 20px; margin: 24px 0;">
          <p style="margin: 0 0 8px 0; color: #6B7280; font-size: 14px;">YOUR LOGIN DETAILS</p>
          <p style="margin: 4px 0;"><strong>Email:</strong> {to_email}</p>
          <p style="margin: 4px 0;"><strong>Password:</strong> <span style="font-family: monospace; font-size: 16px; color: #059669;">{password}</span></p>
        </div>

        <p style="color: #EF4444; font-size: 14px;">
          ⚠️ Please change your password after your first login for security.
        </p>

        <a href="{APP_URL}/login"
           style="display: inline-block; background: #059669; color: white; padding: 12px 28px;
                  border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 16px;">
          Login to {APP_NAME}
        </a>

        <hr style="margin: 32px 0; border: none; border-top: 1px solid #E5E7EB;">
        <p style="color: #9CA3AF; font-size: 12px;">
          If you did not expect this email, please contact your school administrator.<br>
          &copy; {APP_NAME}
        </p>

      </div>
    </body>
    </html>
    """
    _send_email(to_email, subject, html_body)


# Welcome email for new school admin
def send_admin_welcome_email(
    to_email: str,
    first_name: str,
    school_name: str,
    password: str,
) -> None:
    subject = f"Welcome to {APP_NAME} — Admin Account Created"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 30px;">
      <div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color: #2563EB;">Welcome to {APP_NAME}! 🏫</h2>

        <p>Hi <strong>{first_name}</strong>,</p>

        <p>Your admin account has been created for <strong>{school_name}</strong>.</p>
        <p>You can log in to manage teachers, students, classes, and content for your school.</p>

        <div style="background: #F3F4F6; border-radius: 8px; padding: 20px; margin: 24px 0;">
          <p style="margin: 0 0 8px 0; color: #6B7280; font-size: 14px;">YOUR LOGIN DETAILS</p>
          <p style="margin: 4px 0;"><strong>Email:</strong> {to_email}</p>
          <p style="margin: 4px 0;"><strong>Password:</strong> <span style="font-family: monospace; font-size: 16px; color: #2563EB;">{password}</span></p>
        </div>

        <p style="color: #EF4444; font-size: 14px;">
          ⚠️ For security, please change your password after your first login.
        </p>

        <a href="{APP_URL}/login"
           style="display: inline-block; background: #2563EB; color: white; padding: 12px 28px;
                  border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 16px;">
          Login to {APP_NAME}
        </a>

        <hr style="margin: 32px 0; border: none; border-top: 1px solid #E5E7EB;">
        <p style="color: #9CA3AF; font-size: 12px;">
          If you did not expect this email, please contact your platform administrator.<br>
          &copy; {APP_NAME}
        </p>

      </div>
    </body>
    </html>
    """
    _send_email(to_email, subject, html_body)
