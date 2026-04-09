"""
Test SendGrid Email Configuration
Sends a test email to verify SendGrid is working
"""
import os
from dotenv import load_dotenv
from email_sender import send_email

# Load environment variables
load_dotenv()

def test_sendgrid():
    """Test SendGrid configuration"""
    print("\n" + "="*60)
    print("SendGrid Configuration Test")
    print("="*60)

    # Check configuration
    api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_FROM_EMAIL', 'kb-assist@trendmicro.com')
    from_name = os.getenv('SENDGRID_FROM_NAME', 'KB Assist System')

    print(f"\n📧 Configuration:")
    print(f"   API Key: {'✅ Set' if api_key and api_key != 'YOUR_SENDGRID_API_KEY_HERE' else '❌ Not set'}")
    print(f"   From Email: {from_email}")
    print(f"   From Name: {from_name}")

    if not api_key or api_key == 'YOUR_SENDGRID_API_KEY_HERE':
        print("\n❌ SendGrid API key not configured!")
        print("\n📝 Steps to configure:")
        print("   1. Follow AZURE_SENDGRID_SETUP.md")
        print("   2. Add SENDGRID_API_KEY to .env file")
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

    # Send test email
    result = send_email(
        to_email=test_email,
        subject="KB Assist - SendGrid Test Email",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #d71921;">✅ SendGrid Configuration Successful!</h2>
            <p>This is a test email from KB Assist System.</p>
            <p>If you're receiving this email, it means:</p>
            <ul>
                <li>✅ SendGrid API key is configured correctly</li>
                <li>✅ Sender email is verified</li>
                <li>✅ Email sending is working</li>
            </ul>
            <p>You can now proceed with Phase 2 implementation.</p>
            <hr>
            <p style="font-size: 12px; color: #666;">
                This is an automated test email from KB Assist System.
            </p>
        </body>
        </html>
        """,
        text_content="""
KB Assist - SendGrid Test Email

✅ SendGrid Configuration Successful!

This is a test email from KB Assist System.

If you're receiving this email, it means:
- ✅ SendGrid API key is configured correctly
- ✅ Sender email is verified
- ✅ Email sending is working

You can now proceed with Phase 2 implementation.

---
This is an automated test email from KB Assist System.
        """
    )

    print("\n" + "="*60)
    if result['success']:
        print("✅ SUCCESS!")
        print(f"✅ Test email sent to: {test_email}")
        print(f"📬 Message ID: {result.get('email_id', 'N/A')}")
        print("\n📧 Check your inbox (and spam folder)")
        print("\n✅ SendGrid is configured correctly!")
        print("="*60)
        return True
    else:
        print("❌ FAILED!")
        print(f"Error: {result['message']}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your SendGrid API key is correct")
        print("   2. Verify sender email in SendGrid dashboard")
        print("   3. Check SendGrid account status")
        print("   4. See AZURE_SENDGRID_SETUP.md for details")
        print("="*60)
        return False

if __name__ == '__main__':
    try:
        test_sendgrid()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
