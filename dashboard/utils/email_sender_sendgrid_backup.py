"""
Email Sender Module for KB Assist
Sends notifications using Azure SendGrid
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sys

# Add database to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))

# Load environment variables
load_dotenv()

# SendGrid configuration
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'kb-assist@trendmicro.com')
FROM_NAME = os.getenv('SENDGRID_FROM_NAME', 'KB Assist System')
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
        dict: {success: bool, message: str, email_id: str}
    """
    try:
        # Calculate expiration date
        expiration_date = datetime.now() + timedelta(days=LINK_EXPIRATION_DAYS)
        expiration_str = expiration_date.strftime('%B %d, %Y')

        # Build email content
        subject = f"KB Request Rejected - Action Required [{request_id}]"

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #d71921; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .feedback-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #d71921; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .info-box {{ background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>KB Request Needs Revision</h1>
                </div>

                <div class="content">
                    <p>Hi {engineer_name},</p>

                    <p>Your KB request has been reviewed and needs revision before it can be approved.</p>

                    <div class="info-box">
                        <strong>Request ID:</strong> {request_id}<br>
                        {'<strong>Product:</strong> ' + product + '<br>' if product else ''}
                        {'<strong>Issue:</strong> ' + issue_title + '<br>' if issue_title else ''}
                        <strong>Status:</strong> Rejected - Revision Required
                    </div>

                    <h3>📝 Manager's Feedback:</h3>
                    <div class="feedback-box">
                        {feedback_text.replace(chr(10), '<br>')}
                    </div>

                    {'<p><strong>KB Reference:</strong> <a href="' + kb_link + '">' + kb_link + '</a></p>' if kb_link else ''}

                    <h3>✏️ Next Steps:</h3>
                    <p>Please revise your submission based on the feedback above.</p>

                    <center>
                        <a href="{revision_link}" class="button">📝 REVISE YOUR REQUEST</a>
                    </center>

                    <p style="font-size: 12px; color: #666;">
                        This link will expire on {expiration_str}.<br>
                        If the link expires, please resubmit your request.
                    </p>
                </div>

                <div class="footer">
                    <p>This is an automated email from KB Assist System.<br>
                    Questions? Contact your KB manager or IT support.</p>
                </div>
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

        # Send email using SendGrid
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
        subject = f"KB Request Approved - Please Verify [{request_id}]"

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .success-box {{ background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; }}
                .kb-link {{ background-color: #fff; border: 2px solid #28a745; padding: 15px; margin: 15px 0; text-align: center; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #28a745; color: white; text-decoration: none; border-radius: 4px; margin: 10px 5px; }}
                .button-secondary {{ background-color: #ffc107; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ KB Request Approved!</h1>
                </div>

                <div class="content">
                    <p>Hi {engineer_name},</p>

                    <p>Great news! Your KB request has been approved and a KB article has been created.</p>

                    <div class="success-box">
                        <strong>Request ID:</strong> {request_id}<br>
                        {'<strong>Product:</strong> ' + product + '<br>' if product else ''}
                        {'<strong>Your Issue:</strong> ' + issue_title + '<br>' if issue_title else ''}
                        <strong>Status:</strong> ✅ Approved
                    </div>

                    <h3>📄 KB Article Created:</h3>
                    <div class="kb-link">
                        <a href="{kb_link}" style="font-size: 16px; color: #d71921; text-decoration: none;">
                            <strong>{kb_link}</strong>
                        </a>
                        <br><br>
                        <a href="{kb_link}" class="button">📖 VIEW KB ARTICLE</a>
                    </div>

                    <h3>✅ Please Verify:</h3>
                    <p>Review the KB article and confirm it addresses your reported issue.</p>

                    <center>
                        <a href="{verification_link}" class="button">✅ VERIFY KB</a>
                    </center>

                    <p style="font-size: 14px; margin-top: 20px;">
                        <strong>Actions you can take:</strong><br>
                        • Click "Verified" if the KB article is correct<br>
                        • Click "Request Revisions" if changes are needed
                    </p>

                    <p style="font-size: 12px; color: #666; margin-top: 20px;">
                        Thank you for helping improve our Knowledge Base!<br>
                        Your feedback ensures our KBs are accurate and helpful.
                    </p>
                </div>

                <div class="footer">
                    <p>This is an automated email from KB Assist System.<br>
                    Questions? Contact your KB manager or IT support.</p>
                </div>
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
    Send email using SendGrid

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body

    Returns:
        dict: {success: bool, message: str, email_id: str}
    """
    try:
        if not SENDGRID_API_KEY or SENDGRID_API_KEY == 'YOUR_SENDGRID_API_KEY_HERE':
            return {
                'success': False,
                'message': 'SendGrid API key not configured. Please set SENDGRID_API_KEY in .env file.'
            }

        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", text_content),
            html_content=Content("text/html", html_content)
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        return {
            'success': True,
            'message': 'Email sent successfully',
            'email_id': response.headers.get('X-Message-Id', '')
        }

    except Exception as e:
        error_msg = str(e)
        print(f"SendGrid Error: {error_msg}")
        return {
            'success': False,
            'message': f'Failed to send email: {error_msg}'
        }

def log_email_notification(request_id, email_type, recipient_email, recipient_name,
                          subject, body, sent_successfully, revision_link=None,
                          verification_link=None, error_message=None):
    """
    Log email notification to database

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
        from azure_db import get_connection_context

        with get_connection_context() as conn:
            cursor = conn.cursor()

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

            print(f"✅ Logged email notification for {request_id}")

    except Exception as e:
        print(f"⚠️ Failed to log email notification: {e}")

if __name__ == '__main__':
    # Test email configuration
    print("="*60)
    print("KB Assist - Email Configuration Test")
    print("="*60)
    print(f"\nSendGrid API Key: {'✅ Configured' if SENDGRID_API_KEY and SENDGRID_API_KEY != 'YOUR_SENDGRID_API_KEY_HERE' else '❌ Not configured'}")
    print(f"From Email: {FROM_EMAIL}")
    print(f"From Name: {FROM_NAME}")
    print(f"Base URL: {BASE_URL}")
    print(f"Link Expiration: {LINK_EXPIRATION_DAYS} days")
    print("="*60)
