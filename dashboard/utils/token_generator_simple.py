"""
Simple Token Generator for Revision/Verification Links
Generates secure tokens without database dependency
"""
import secrets

def generate_token(request_id, token_type='revision'):
    """
    Generate a secure token for revision or verification links

    Args:
        request_id: Request ID (e.g., REQ-000123)
        token_type: 'revision' or 'verification'

    Returns:
        str: Secure URL-safe token
    """
    # Generate a cryptographically secure random token
    token = secrets.token_urlsafe(32)
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
