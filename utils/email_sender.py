"""
Email Sender Module for KB Assist
Sends notifications using Gmail SMTP (FREE!)
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sys

# Add database to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))

# Load environment variables
load_dotenv()

# Gmail SMTP configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', SMTP_USERNAME)
FROM_NAME = os.getenv('SMTP_FROM_NAME', 'KB Assist System')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
LINK_EXPIRATION_DAYS = int(os.getenv('LINK_EXPIRATION_DAYS', 7))

def send_rejection_email(request_id, engineer_email, engineer_name, feedback_text,
                        kb_link=None, product=None, issue_title=None, revision_link=None):
    """
    Send rejection notification email to engineer

    Args:
        request_id: Request ID (e.g., REQ-000123)
        engineer_email: Engineer's email address
        engineer_name: Engineer's name
        feedback_text: Manager's feedback/reason for rejection
        kb_link: Optional KB article link referenced
        product: Product name
        issue_title: Issue title/description
        revision_link: Link to revision portal

    Returns:
        dict: {success: bool, message: str}
    """
    try:
        # Calculate expiration date
        expiration_date = datetime.now() + timedelta(days=LINK_EXPIRATION_DAYS)
        expiration_str = expiration_date.strftime('%B %d, %Y')

        # Build email content
        subject = f"KB Request Rejected - Action Required [{request_id}]"

        # Professional HTML with inline CSS (like CoachAI)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .header {{
                    background-color: #f44336;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    margin: 20px 0;
                    padding: 15px;
                    border-left: 4px solid #f44336;
                    background-color: #f8f9fa;
                    border-radius: 0 5px 5px 0;
                }}
                .details {{
                    background-color: #ffffff;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border: 1px solid #e0e0e0;
                }}
                .feedback-box {{
                    background-color: #fff3cd;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #ffc107;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #f44336;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 15px 0;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                    color: #666;
                    font-size: 12px;
                }}
                h2 {{
                    color: #d71921;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚠️ KB Request Needs Revision</h1>
                <p>Action Required</p>
            </div>

            <p>Hi {engineer_name},</p>
            <p>Your KB request has been reviewed and needs revision before it can be approved.</p>

            <div class="section">
                <h2>📋 Request Information</h2>
                <div class="details">
                    <strong>Request ID:</strong> {request_id}<br>
                    {'<strong>Product:</strong> ' + product + '<br>' if product else ''}
                    {'<strong>Issue:</strong> ' + issue_title + '<br>' if issue_title else ''}
                    <strong>Status:</strong> <span style="color: #f44336; font-weight: bold;">Rejected - Revision Required</span>
                </div>
            </div>

            <div class="section">
                <h2>💡 Manager's Feedback</h2>
                <div class="feedback-box">
                    {feedback_text.replace(chr(10), '<br>')}
                </div>
            </div>

            {'<div class="section"><h2>📚 KB Reference</h2><div class="details">' + kb_link + '</div></div>' if kb_link else ''}

            <div class="section">
                <h2>✏️ Next Steps</h2>
                <div class="details">
                    <p><strong>Ready to revise your submission?</strong></p>
                    <p>Click the button below to access the revision portal where you can:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>View your original submission and the detailed feedback</li>
                        <li>Update your PERTS and troubleshooting steps</li>
                        <li>Use the AI assistant to improve your content</li>
                        <li>Submit your revision for review</li>
                    </ul>
                    <center>
                        <a href="{revision_link}" class="button">✏️ Revise Your Submission</a>
                    </center>
                    <p style="font-size: 12px; color: #666; margin-top: 15px;">
                        <em>This link will expire on {expiration_str}. For assistance, contact your KB manager.</em>
                    </p>
                </div>
            </div>

            <div class="footer">
                <p>This is an automated email from KB Assist System.</p>
                <p>Questions? Contact your KB manager or IT support.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
KB Request Rejected - Action Required [{request_id}]

Hi {engineer_name},

Your KB request has been reviewed and needs revision before it can be approved.

Request ID: {request_id}
{'Product: ' + product if product else ''}
{'Issue: ' + issue_title if issue_title else ''}
Status: Rejected - Revision Required

MANAGER'S FEEDBACK:
{feedback_text}

{'KB Reference: ' + kb_link if kb_link else ''}

NEXT STEPS:
Please revise your submission based on the feedback above.

REVISE YOUR REQUEST:
{revision_link}

This link will expire on {expiration_str}.
If the link expires, please resubmit your request.

---
This is an automated email from KB Assist System.
Questions? Contact your KB manager or IT support.
        """

        # Send email using Gmail SMTP
        result = send_email(
            to_email=engineer_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        # Log email notification
        if result['success']:
            log_email_notification(
                request_id=request_id,
                email_type='rejection',
                recipient_email=engineer_email,
                recipient_name=engineer_name,
                subject=subject,
                body=text_content,
                sent_successfully=True,
                revision_link=revision_link
            )

        return result

    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending rejection email: {str(e)}'
        }

def send_approval_email(request_id, engineer_email, engineer_name, kb_link,
                       product=None, issue_title=None, verification_link=None):
    """
    Send approval notification email to engineer

    Args:
        request_id: Request ID
        engineer_email: Engineer's email
        engineer_name: Engineer's name
        kb_link: Link to created/updated KB article
        product: Product name
        issue_title: Issue title
        verification_link: Link to verification portal

    Returns:
        dict: {success: bool, message: str}
    """
    try:
        subject = f"KB Request Approved - KB Article Published [{request_id}]"

        # Professional HTML with inline CSS (like CoachAI) - Success theme
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .header {{
                    background-color: #28a745;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    margin: 20px 0;
                    padding: 15px;
                    border-left: 4px solid #28a745;
                    background-color: #f8f9fa;
                    border-radius: 0 5px 5px 0;
                }}
                .details {{
                    background-color: #ffffff;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border: 1px solid #e0e0e0;
                }}
                .kb-box {{
                    background-color: #d4edda;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #28a745;
                    text-align: center;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 5px;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                    color: #666;
                    font-size: 12px;
                }}
                h2 {{
                    color: #1976D2;
                    margin-bottom: 10px;
                }}
                ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                li {{
                    margin: 5px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ KB Request Approved!</h1>
                <p>Your contribution has been published</p>
            </div>

            <p>Hi {engineer_name},</p>
            <p>Great news! Your KB request has been approved and a KB article has been created.</p>

            <div class="section">
                <h2>📋 Request Information</h2>
                <div class="details">
                    <strong>Request ID:</strong> {request_id}<br>
                    {'<strong>Product:</strong> ' + product + '<br>' if product else ''}
                    {'<strong>Your Issue:</strong> ' + issue_title + '<br>' if issue_title else ''}
                    <strong>Status:</strong> <span style="color: #28a745; font-weight: bold;">✅ Approved</span>
                </div>
            </div>

            <div class="section">
                <h2>📄 KB Article Created</h2>
                <div class="kb-box">
                    <p style="font-size: 16px; margin: 10px 0;">
                        <a href="{kb_link}" style="color: #d71921; text-decoration: none; font-weight: bold;">{kb_link}</a>
                    </p>
                    <a href="{kb_link}" class="button">📖 View KB Article</a>
                </div>
            </div>

            <div class="section">
                <h2>✅ Next Steps</h2>
                <div class="details">
                    <p><strong>Please review the KB article:</strong></p>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Click the "View KB Article" button above to review the published article</li>
                        <li>Verify it addresses your reported issue correctly</li>
                        <li>If everything looks good, no further action is needed!</li>
                        <li>If revisions are needed, contact your KB manager with the Request ID (<strong>{request_id}</strong>)</li>
                    </ol>
                    <p style="margin-top: 15px; padding: 10px; background-color: #d4edda; border-left: 4px solid #28a745; border-radius: 3px;">
                        <strong>✅ Thank you!</strong> Your contribution helps improve our Knowledge Base and assists other engineers in resolving similar issues.
                    </p>
                </div>
            </div>

            <div class="footer">
                <p><em>Thank you for helping improve our Knowledge Base!</em></p>
                <p><em>Your feedback ensures our KBs are accurate and helpful.</em></p>
                <p style="margin-top: 15px;">This is an automated email from KB Assist System.</p>
                <p>Questions? Contact your KB manager or IT support.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
KB Request Approved - Please Verify [{request_id}]

Hi {engineer_name},

Great news! Your KB request has been approved and a KB article has been created.

Request ID: {request_id}
{'Product: ' + product if product else ''}
{'Your Issue: ' + issue_title if issue_title else ''}
Status: ✅ Approved

KB ARTICLE CREATED:
{kb_link}

PLEASE VERIFY:
Review the KB article and confirm it addresses your reported issue.

VERIFY KB:
{verification_link}

Actions you can take:
• Click "Verified" if the KB article is correct
• Click "Request Revisions" if changes are needed

Thank you for helping improve our Knowledge Base!
Your feedback ensures our KBs are accurate and helpful.

---
This is an automated email from KB Assist System.
Questions? Contact your KB manager or IT support.
        """

        # Send email
        result = send_email(
            to_email=engineer_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        # Log email notification
        if result['success']:
            log_email_notification(
                request_id=request_id,
                email_type='approval',
                recipient_email=engineer_email,
                recipient_name=engineer_name,
                subject=subject,
                body=text_content,
                sent_successfully=True,
                verification_link=verification_link
            )

        return result

    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending approval email: {str(e)}'
        }

def send_email(to_email, subject, html_content, text_content):
    """
    Send email using Gmail SMTP

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body

    Returns:
        dict: {success: bool, message: str}
    """
    try:
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            return {
                'success': False,
                'message': 'Gmail SMTP credentials not configured. Please set SMTP_USERNAME and SMTP_PASSWORD in .env file.'
            }

        # DEBUG: Log recipient
        print(f"DEBUG EMAIL: Sending to: '{to_email}'")
        print(f"DEBUG EMAIL: Subject: '{subject}'")
        print(f"DEBUG EMAIL: From: '{FROM_EMAIL}'")

        # Create message - USE COACHUI METHOD (HTML only, simple From)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL  # Simple From (no fancy name)
        msg['To'] = to_email

        # HTML ONLY (no plain text part) - like CoachAI
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Connect to Gmail SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(0)  # Set to 1 for debugging

        if SMTP_USE_TLS:
            server.starttls()

        # Login
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print(f"DEBUG EMAIL: SMTP login successful")

        # Send email - USE SENDMAIL like CoachAI (not send_message)
        recipients = [to_email]
        print(f"🔍 CRITICAL DEBUG:")
        print(f"   FROM_EMAIL = {FROM_EMAIL}")
        print(f"   to_email param = {to_email}")
        print(f"   recipients list = {recipients}")
        print(f"   msg['To'] header = {msg['To']}")
        print(f"   msg['From'] header = {msg['From']}")

        refused = server.sendmail(FROM_EMAIL, recipients, msg.as_string())

        if refused:
            print(f"⚠️  Some recipients were refused: {refused}")
        else:
            print(f"✅ Email sent successfully to {recipients}")

        server.quit()

        return {
            'success': True,
            'message': 'Email sent successfully via Gmail'
        }

    except smtplib.SMTPAuthenticationError as e:
        error_msg = f'Authentication failed. Check your Gmail App Password: {str(e)}'
        print(f"Gmail SMTP Error: {error_msg}")
        return {
            'success': False,
            'message': error_msg
        }

    except smtplib.SMTPException as e:
        error_msg = f'SMTP error: {type(e).__name__}: {str(e) if str(e) else "Unknown SMTP error"}'
        print(f"Gmail SMTP Error: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': error_msg
        }

    except Exception as e:
        error_msg = f'Failed to send email: {type(e).__name__}: {str(e) if str(e) else "Unknown error"}'
        print(f"Error: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': error_msg
        }

def log_email_notification(request_id, email_type, recipient_email, recipient_name,
                          subject, body, sent_successfully, revision_link=None,
                          verification_link=None, error_message=None):
    """
    Log email notification to SQLite database

    Args:
        request_id: Request ID
        email_type: 'rejection', 'approval', 'verification_reminder'
        recipient_email: Recipient's email
        recipient_name: Recipient's name
        subject: Email subject
        body: Email body (text)
        sent_successfully: Boolean
        revision_link: Revision portal link (if applicable)
        verification_link: Verification portal link (if applicable)
        error_message: Error message (if failed)
    """
    try:
        import sqlite3
        from datetime import datetime

        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'kb_assist.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                email_type TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                subject TEXT,
                body TEXT,
                sent_successfully BOOLEAN DEFAULT 0,
                error_message TEXT,
                revision_link TEXT,
                verification_link TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO email_notifications (
                request_id, email_type, recipient_email, recipient_name,
                subject, body, sent_successfully, error_message,
                revision_link, verification_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, email_type, recipient_email, recipient_name,
            subject, body, sent_successfully, error_message,
            revision_link, verification_link
        ))

        conn.commit()
        conn.close()
        print(f"✅ Logged email notification for {request_id}")

    except Exception as e:
        print(f"⚠️ Failed to log email notification: {e}")

def send_cancellation_email(request_id, engineer_email, engineer_name, reason, reviewed_by):
    """
    Send cancellation notification email to engineer

    Args:
        request_id: Request ID (e.g., REQ-000123)
        engineer_email: Engineer's email address
        engineer_name: Engineer's name
        reason: Reason for cancellation
        reviewed_by: Manager who cancelled the request

    Returns:
        dict: {success: bool, message: str, error: str (if failed)}
    """
    try:
        # Build email content
        subject = f"KB Request Cancelled [{request_id}]"

        # Professional HTML with inline CSS
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .header {{
                    background-color: #6c757d;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    margin: 20px 0;
                    padding: 15px;
                    border-left: 4px solid #6c757d;
                    background-color: #f8f9fa;
                    border-radius: 0 5px 5px 0;
                }}
                .details {{
                    background-color: #ffffff;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border: 1px solid #e0e0e0;
                }}
                .reason-box {{
                    background-color: #f8d7da;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #dc3545;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 2px solid #e0e0e0;
                    color: #6c757d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>❌ KB Request Cancelled</h2>
            </div>

            <p>Hello {engineer_name},</p>

            <p>Your KB request <strong>{request_id}</strong> has been cancelled by the manager.</p>

            <div class="details">
                <p><strong>Request ID:</strong> {request_id}</p>
                <p><strong>Cancelled by:</strong> {reviewed_by}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>

            <div class="reason-box">
                <p><strong>Reason for Cancellation:</strong></p>
                <p style="white-space: pre-wrap; margin: 0;">{reason}</p>
            </div>

            <div class="section">
                <p><strong>What does this mean?</strong></p>
                <p>This request will not be processed. No further action is required from you.</p>
                <p>If you believe this was done in error or have questions, please contact the manager: <strong>{reviewed_by}</strong></p>
            </div>

            <div class="footer">
                <p>This is an automated notification from KB Assist System.</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """

        # Plain text fallback
        text_content = f"""
KB Request Cancelled

Hello {engineer_name},

Your KB request {request_id} has been cancelled by the manager.

Request ID: {request_id}
Cancelled by: {reviewed_by}
Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

Reason for Cancellation:
{reason}

What does this mean?
This request will not be processed. No further action is required from you.

If you believe this was done in error or have questions, please contact the manager: {reviewed_by}

---
This is an automated notification from KB Assist System.
Please do not reply to this email.
        """

        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        message['To'] = engineer_email

        # Attach both text and HTML
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        message.attach(part1)
        message.attach(part2)

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)

        print(f"✅ Cancellation email sent to {engineer_email} for {request_id}")

        # Log email
        log_email_notification(
            request_id=request_id,
            email_type='cancellation',
            recipient_email=engineer_email,
            recipient_name=engineer_name,
            subject=subject,
            body=html_content,
            sent_successfully=True
        )

        return {
            'success': True,
            'message': f'Cancellation email sent to {engineer_email}'
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to send cancellation email: {error_msg}")

        # Log failed email
        log_email_notification(
            request_id=request_id,
            email_type='cancellation',
            recipient_email=engineer_email,
            recipient_name=engineer_name,
            subject=subject if 'subject' in locals() else 'Cancellation Email',
            body='Email failed to send',
            sent_successfully=False,
            error_message=error_msg
        )

        return {
            'success': False,
            'message': 'Failed to send email',
            'error': error_msg
        }

def send_submission_confirmation_email(request_id, engineer_email, engineer_name, request_type, product, kb_article_id=None):
    """
    Send confirmation email when engineer submits a KB request

    Args:
        request_id: Request ID (e.g., REQ-000123)
        engineer_email: Engineer's email address
        engineer_name: Engineer's name
        request_type: Type of request (kb_update_request or no_kb_exists)
        product: Product name
        kb_article_id: KB article ID (if update request)

    Returns:
        dict: {success: bool, message: str, error: str (if failed)}
    """
    try:
        # Determine request type display
        if request_type == 'kb_update_request':
            type_display = f"KB Update Request for KB-{kb_article_id}"
            type_emoji = "🔄"
        else:
            type_display = "New KB Request"
            type_emoji = "➕"

        subject = f"✅ Submission Confirmed [{request_id}]"

        # HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .header {{
                    background-color: #28a745;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    margin: 20px 0;
                    padding: 15px;
                    border-left: 4px solid #28a745;
                    background-color: #f8f9fa;
                    border-radius: 0 5px 5px 0;
                }}
                .details {{
                    background-color: #ffffff;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 12px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Submission Received!</h1>
            </div>

            <p>Hi {engineer_name},</p>

            <p>Thank you for your contribution! Your KB request has been successfully submitted and is now being reviewed by the KB team.</p>

            <div class="section">
                <h3>Submission Details</h3>
                <div class="details">
                    <p><strong>{type_emoji} Request Type:</strong> {type_display}</p>
                    <p><strong>📋 Request ID:</strong> {request_id}</p>
                    <p><strong>📦 Product:</strong> {product}</p>
                    <p><strong>📅 Submitted:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
            </div>

            <div class="section">
                <h3>What Happens Next?</h3>
                <ol>
                    <li><strong>AI Validation</strong> - Your submission is checked for duplicates</li>
                    <li><strong>SDC Review</strong> - KB team reviews your proposed changes</li>
                    <li><strong>Feedback/Approval</strong> - You'll receive an email with the decision</li>
                </ol>
                <p>💡 <strong>Tip:</strong> You can expect a response within 2-3 business days. If the team needs more information, they'll send you a follow-up email with a revision link.</p>
            </div>

            <div class="footer">
                <p>This is an automated notification from KB Assist.</p>
                <p>Questions? Contact your KB team manager.</p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
✅ KB SUBMISSION CONFIRMED

Hi {engineer_name},

Thank you for your contribution! Your KB request has been successfully submitted.

SUBMISSION DETAILS:
{type_emoji} Request Type: {type_display}
📋 Request ID: {request_id}
📦 Product: {product}
📅 Submitted: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

WHAT HAPPENS NEXT:
1. AI Validation - Your submission is checked for duplicates
2. SDC Review - KB team reviews your proposed changes
3. Feedback/Approval - You'll receive an email with the decision

💡 Tip: You can expect a response within 2-3 business days.

---
This is an automated notification from KB Assist.
Questions? Contact your KB team manager.
        """

        # Send email
        result = send_email(engineer_email, subject, html_content, text_content)

        if result['success']:
            # Log successful email
            log_email_notification(
                request_id=request_id,
                email_type='submission_confirmation',
                recipient_email=engineer_email,
                recipient_name=engineer_name,
                subject=subject,
                body=html_content,
                sent_successfully=True
            )

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to send submission confirmation email: {error_msg}")

        return {
            'success': False,
            'message': 'Failed to send email',
            'error': error_msg
        }


def send_ai_auto_rejection_email(request_id, engineer_email, engineer_name, kb_article_id, kb_title,
                                  reasoning, existing_content=None, confidence=0.9):
    """
    Send email when AI auto-rejects a duplicate KB update submission

    Args:
        request_id: Request ID (e.g., REQ-000123)
        engineer_email: Engineer's email address
        engineer_name: Engineer's name
        kb_article_id: KB article number
        kb_title: KB article title
        reasoning: AI's reasoning for rejection
        existing_content: Existing KB content that covers the solution (optional)
        confidence: AI confidence level (0-1)

    Returns:
        dict: {success: bool, message: str, error: str (if failed)}
    """
    try:
        subject = f"⚠️ Submission Auto-Declined - Already Covered [{request_id}]"

        # Build confidence display
        confidence_pct = int(confidence * 100)
        if confidence >= 0.9:
            confidence_label = "Very High"
            confidence_color = "#dc3545"
        elif confidence >= 0.7:
            confidence_label = "High"
            confidence_color = "#fd7e14"
        else:
            confidence_label = "Moderate"
            confidence_color = "#ffc107"

        # HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .header {{
                    background-color: #ffc107;
                    color: #000;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    margin: 20px 0;
                    padding: 15px;
                    border-left: 4px solid #ffc107;
                    background-color: #fffbf0;
                    border-radius: 0 5px 5px 0;
                }}
                .ai-decision {{
                    background-color: #fff3cd;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 10px 0;
                    border: 1px solid #ffc107;
                }}
                .existing-content {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-left: 4px solid #6c757d;
                    margin: 10px 0;
                    font-family: monospace;
                    font-size: 13px;
                    white-space: pre-wrap;
                }}
                .kb-link {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #0066cc;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 12px;
                    text-align: center;
                }}
                .confidence-badge {{
                    display: inline-block;
                    padding: 5px 10px;
                    background-color: {confidence_color};
                    color: white;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 AI Duplicate Detection</h1>
                <h3>Submission Automatically Declined</h3>
            </div>

            <p>Hi {engineer_name},</p>

            <p>Thank you for your submission! Our AI system has reviewed your proposed KB update for <strong>KB-{kb_article_id}</strong> and determined that the solution is already covered in the current KB article.</p>

            <div class="section">
                <h3>📋 Submission Details</h3>
                <p><strong>Request ID:</strong> {request_id}</p>
                <p><strong>KB Article:</strong> KB-{kb_article_id} - {kb_title}</p>
                <p><strong>AI Confidence:</strong> <span class="confidence-badge">{confidence_label} ({confidence_pct}%)</span></p>
            </div>

            <div class="ai-decision">
                <h3>🤖 AI Analysis</h3>
                <p><strong>Decision:</strong> Auto-Rejected (Duplicate Content)</p>
                <p><strong>Reasoning:</strong> {reasoning}</p>
            </div>

            {f'''
            <div class="section">
                <h3>📄 Existing KB Content</h3>
                <p>The following content from the current KB already covers your proposed solution:</p>
                <div class="existing-content">{existing_content[:500]}{'...' if len(existing_content) > 500 else ''}</div>
            </div>
            ''' if existing_content else ''}

            <div class="section">
                <h3>✅ What You Can Do</h3>
                <ul>
                    <li><strong>Review the KB:</strong> Check if the current KB fully addresses the issue</li>
                    <li><strong>Different Scenario?</strong> If your case is different, you can resubmit with more specific details</li>
                    <li><strong>Disagree?</strong> Contact your KB team manager for manual review</li>
                </ul>
                <a href="https://helpcenter.trendmicro.com/en-us/article/tmka-{kb_article_id}" class="kb-link">📖 View KB-{kb_article_id}</a>
            </div>

            <div class="footer">
                <p>This is an automated decision by KB Assist AI.</p>
                <p>Questions or concerns? Contact your KB team manager for a manual review.</p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
🤖 AI DUPLICATE DETECTION - SUBMISSION AUTO-DECLINED

Hi {engineer_name},

Thank you for your submission! Our AI system has reviewed your proposed KB update for KB-{kb_article_id} and determined that the solution is already covered in the current KB article.

SUBMISSION DETAILS:
Request ID: {request_id}
KB Article: KB-{kb_article_id} - {kb_title}
AI Confidence: {confidence_label} ({confidence_pct}%)

AI ANALYSIS:
Decision: Auto-Rejected (Duplicate Content)
Reasoning: {reasoning}

{f'EXISTING KB CONTENT:\n{existing_content[:300]}...\n' if existing_content else ''}

WHAT YOU CAN DO:
- Review the KB: Check if the current KB fully addresses the issue
- Different Scenario? If your case is different, you can resubmit with more specific details
- Disagree? Contact your KB team manager for manual review

View KB: https://helpcenter.trendmicro.com/en-us/article/tmka-{kb_article_id}

---
This is an automated decision by KB Assist AI.
Questions or concerns? Contact your KB team manager for a manual review.
        """

        # Send email
        result = send_email(engineer_email, subject, html_content, text_content)

        if result['success']:
            # Log successful email
            log_email_notification(
                request_id=request_id,
                email_type='ai_auto_rejection',
                recipient_email=engineer_email,
                recipient_name=engineer_name,
                subject=subject,
                body=html_content,
                sent_successfully=True
            )

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to send AI auto-rejection email: {error_msg}")

        return {
            'success': False,
            'message': 'Failed to send email',
            'error': error_msg
        }


if __name__ == '__main__':
    # Test email configuration
    print("="*60)
    print("KB Assist - Gmail Email Configuration Test")
    print("="*60)
    print(f"\nGmail SMTP Settings:")
    print(f"  Server: {SMTP_SERVER}")
    print(f"  Port: {SMTP_PORT}")
    print(f"  TLS: {'✅ Enabled' if SMTP_USE_TLS else '❌ Disabled'}")
    print(f"  Username: {'✅ Configured' if SMTP_USERNAME else '❌ Not configured'}")
    print(f"  Password: {'✅ Configured' if SMTP_PASSWORD else '❌ Not configured'}")
    print(f"  From Email: {FROM_EMAIL}")
    print(f"  From Name: {FROM_NAME}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Link Expiration: {LINK_EXPIRATION_DAYS} days")
    print("="*60)
