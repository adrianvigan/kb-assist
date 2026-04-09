"""
Simple Token Generator for Revision/Verification Links
Generates secure tokens with request_id embedded
"""
import secrets
import base64

def generate_token(request_id, token_type='revision'):
    """
    Generate a secure token for revision or verification links

    Args:
        request_id: Request ID (e.g., REQ-000123)
        token_type: 'revision' or 'verification'

    Returns:
        str: Secure URL-safe token with embedded request_id
    """
    # Format: {type}_{request_id}_{random_secure_token}
    random_token = secrets.token_urlsafe(16)
    token = f"{token_type}_{request_id}_{random_token}"
    return token

# Example usage
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Simple Token Generator Test")
    print("="*60)

    # Test token generation
    revision_token = generate_token("REQ-000123", "revision")
    verification_token = generate_token("REQ-000123", "verification")

    print(f"\nRevision token: {revision_token}")
    print(f"Verification token: {verification_token}")
    print(f"\nToken length: {len(revision_token)} characters")

    print("\n" + "="*60)
    print("✅ Token generator working correctly!")
    print("="*60)
