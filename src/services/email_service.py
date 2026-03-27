"""
email_service.py
----------------
Sends emails via Brevo (formerly Sendinblue) API.
Works perfectly on Render (no SMTP blocking issues).

Required .env variables:
  BREVO_API_KEY=your_brevo_api_key
  BREVO_SENDER_EMAIL=your-email@example.com
  APP_NAME=Padhai App
  APP_URL=https://yourapp.com

How to get Brevo API Key:
  1. Sign up at https://brevo.com (free account)
  2. Go to Settings → SMTP & API → API Keys
  3. Create a new API key and copy it
  4. Use that key in BREVO_API_KEY
  5. Verify your sender email in Settings → Senders & Signatures

Free tier: 300 emails per day (unlimited)
"""

import os
import requests
from fastapi import HTTPException, status

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
APP_NAME = os.getenv("APP_NAME", "Padhai App")
APP_URL = os.getenv("APP_URL", "https://yourapp.com")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Core Brevo API send function.
    All other functions in this file call this.
    """
    if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service not configured. Set BREVO_API_KEY and BREVO_SENDER_EMAIL in .env",
        )

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "sender": {
            "name": APP_NAME,
            "email": BREVO_SENDER_EMAIL
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject,
        "htmlContent": html_body,
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code not in [200, 201]:
            error_detail = response.json().get("message", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {error_detail}",
            )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service timeout. Please try again.",
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email service error: {str(e)}",
        )


# Welcome email for new student
def send_student_welcome_email(
    to_email: str,
    first_name: str,
    school_name: str,
    password: str,
    grade_level: int,
    section: str,
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