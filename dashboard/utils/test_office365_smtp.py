"""
Test Office 365 SMTP Configuration
Sends a test email to verify Office 365 SMTP is working
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_office365_smtp():
    """Test Office 365 SMTP configuration"""
    print("\n" + "="*60)
    print("Office 365 SMTP Configuration Test")
    print("="*60)

    # Check configuration
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.office365.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('SMTP_FROM_EMAIL', smtp_username)
    from_name = os.getenv('SMTP_FROM_NAME', 'KB Assist System')

    print(f"\n📧 Configuration:")
    print(f"   Server: {smtp_server}")
    print(f"   Port: {smtp_port}")
    print(f"   Username: {smtp_username if smtp_username else '❌ Not set'}")
    print(f"   Password: {'✅ Set' if smtp_password else '❌ Not set'}")
    print(f"   From Email: {from_email}")
    print(f"   From Name: {from_name}")

    if not smtp_username or not smtp_password:
        print("\n❌ Office 365 SMTP credentials not configured!")
        print("\n📝 Steps to configure:")
        print("   1. Follow OFFICE365_SMTP_SETUP.md")
        print("   2. Add SMTP_USERNAME and SMTP_PASSWORD to .env file")
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
        msg['Subject'] = "KB Assist - Office 365 SMTP Test Email"
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = test_email

        # Plain text version
        text_content = """
KB Assist - Office 365 SMTP Test Email

✅ Office 365 SMTP Configuration Successful!

This is a test email from KB Assist System using Office 365 SMTP.

If you're receiving this email, it means:
- ✅ Office 365 SMTP credentials are configured correctly
- ✅ Sender email is authenticated
- ✅ Email sending is working
- ✅ You can proceed with Phase 2 implementation

Next steps:
1. Deploy API to Azure (get permanent URL)
2. Update BASE_URL in .env
3. Test rejection workflow

---
This is an automated test email from KB Assist System.
        """

        # HTML version
        html_content = """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #d71921;">✅ Office 365 SMTP Configuration Successful!</h2>
            <p>This is a test email from KB Assist System using Office 365 SMTP.</p>
            <p>If you're receiving this email, it means:</p>
            <ul>
                <li>✅ Office 365 SMTP credentials are configured correctly</li>
                <li>✅ Sender email is authenticated</li>
                <li>✅ Email sending is working</li>
                <li>✅ You can proceed with Phase 2 implementation</li>
            </ul>
            <h3>Next steps:</h3>
            <ol>
                <li>Deploy API to Azure (get permanent URL)</li>
                <li>Update BASE_URL in .env</li>
                <li>Test rejection workflow</li>
            </ol>
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

        # Connect to Office 365 SMTP
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
        print("\n✅ Office 365 SMTP is configured correctly!")
        print("="*60)
        return True

    except smtplib.SMTPAuthenticationError as e:
        print("\n" + "="*60)
        print("❌ AUTHENTICATION FAILED!")
        print(f"Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your username is correct (full email address)")
        print("   2. Check your password/app password is correct")
        print("   3. If you have MFA enabled, use an App Password")
        print("   4. Remove any spaces from the app password")
        print("\n📖 See OFFICE365_SMTP_SETUP.md for help")
        print("="*60)
        return False

    except smtplib.SMTPException as e:
        print("\n" + "="*60)
        print("❌ SMTP ERROR!")
        print(f"Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check port 587 is not blocked by firewall")
        print("   2. Verify smtp.office365.com is accessible")
        print("   3. Check with IT if SMTP is blocked")
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
        test_office365_smtp()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
