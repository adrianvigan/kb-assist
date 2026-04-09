"""
Test Gmail SMTP Configuration
Sends a test email to verify Gmail SMTP is working
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gmail_smtp():
    """Test Gmail SMTP configuration"""
    print("\n" + "="*60)
    print("Gmail SMTP Configuration Test")
    print("="*60)

    # Check configuration
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('SMTP_FROM_EMAIL', smtp_username)
    from_name = os.getenv('SMTP_FROM_NAME', 'KB Assist System')

    print(f"\n📧 Configuration:")
    print(f"   Server: {smtp_server}")
    print(f"   Port: {smtp_port}")
    print(f"   Username: {smtp_username if smtp_username else '❌ Not set'}")
    print(f"   Password: {'✅ Set (' + str(len(smtp_password)) + ' chars)' if smtp_password else '❌ Not set'}")
    print(f"   From Email: {from_email}")
    print(f"   From Name: {from_name}")

    if not smtp_username or not smtp_password:
        print("\n❌ Gmail SMTP credentials not configured!")
        print("\n📝 Steps to configure:")
        print("   1. Create Gmail App Password:")
        print("      https://myaccount.google.com/apppasswords")
        print("   2. Add to .env file:")
        print("      SMTP_USERNAME=your-email@gmail.com")
        print("      SMTP_PASSWORD=your-16-char-app-password")
        print("   3. Run this test again")
        return False

    # Get test recipient email
    print("\n" + "="*60)
    test_email = input("Enter your email address for test: ").strip()

    if not test_email or '@' not in test_email:
        print("❌ Invalid email address")
        return False

    print(f"\n📨 Sending test email to: {test_email}")
    print("Please wait...")

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "KB Assist - Gmail SMTP Test Email"
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = test_email

        # Plain text version
        text_content = """
KB Assist - Gmail SMTP Test Email

✅ Gmail SMTP Configuration Successful!

This is a test email from KB Assist System using Gmail SMTP.

If you're receiving this email, it means:
- ✅ Gmail SMTP credentials are configured correctly
- ✅ App password is working
- ✅ Email sending is functional
- ✅ You can proceed with Phase 2 implementation

Next steps:
1. Deploy API to Azure (get permanent URL)
2. Update BASE_URL in .env
3. Test rejection workflow

Note: Gmail allows 500 emails/day for free Gmail accounts,
or 2,000/day for Google Workspace accounts.

---
This is an automated test email from KB Assist System.
        """

        # HTML version
        html_content = """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #d71921;">✅ Gmail SMTP Configuration Successful!</h2>
            <p>This is a test email from KB Assist System using Gmail SMTP.</p>
            <p>If you're receiving this email, it means:</p>
            <ul>
                <li>✅ Gmail SMTP credentials are configured correctly</li>
                <li>✅ App password is working</li>
                <li>✅ Email sending is functional</li>
                <li>✅ You can proceed with Phase 2 implementation</li>
            </ul>
            <h3>Next steps:</h3>
            <ol>
                <li>Deploy API to Azure (get permanent URL)</li>
                <li>Update BASE_URL in .env</li>
                <li>Test rejection workflow</li>
            </ol>
            <p style="background-color: #e7f3ff; padding: 10px; border-left: 4px solid #2196F3;">
                <strong>Note:</strong> Gmail allows 500 emails/day for free Gmail accounts,
                or 2,000/day for Google Workspace accounts.
            </p>
            <hr>
            <p style="font-size: 12px; color: #666;">
                This is an automated test email from KB Assist System.
            </p>
        </body>
        </html>
        """

        # Attach both versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Connect to Gmail SMTP
        print(f"   Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(0)  # Set to 1 for debugging

        print("   Starting TLS...")
        server.starttls()

        print(f"   Authenticating as {smtp_username}...")
        server.login(smtp_username, smtp_password)

        print("   Sending email...")
        server.send_message(msg)
        server.quit()

        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print(f"✅ Test email sent to: {test_email}")
        print("\n📧 Check your inbox (and spam folder)")
        print("\n✅ Gmail SMTP is configured correctly!")
        print("\n📊 Gmail Sending Limits:")
        print("   - Free Gmail: 500 emails/day")
        print("   - Google Workspace: 2,000 emails/day")
        print("="*60)
        return True

    except smtplib.SMTPAuthenticationError as e:
        print("\n" + "="*60)
        print("❌ AUTHENTICATION FAILED!")
        print(f"Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure you're using an APP PASSWORD, not your Gmail password")
        print("   2. Remove spaces from app password (should be 16 chars)")
        print("   3. Enable 2-Step Verification first:")
        print("      https://myaccount.google.com/security")
        print("   4. Then create app password:")
        print("      https://myaccount.google.com/apppasswords")
        print("="*60)
        return False

    except smtplib.SMTPException as e:
        print("\n" + "="*60)
        print("❌ SMTP ERROR!")
        print(f"Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check port 587 is not blocked by firewall")
        print("   2. Verify smtp.gmail.com is accessible")
        print("   3. Check internet connection")
        print("="*60)
        return False

    except Exception as e:
        print("\n" + "="*60)
        print("❌ FAILED!")
        print(f"Error: {e}")
        print("\n🔧 Check your configuration in .env file")
        print("="*60)
        return False

if __name__ == '__main__':
    try:
        test_gmail_smtp()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
