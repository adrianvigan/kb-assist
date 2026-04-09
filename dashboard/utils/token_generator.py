"""
Token Generator for Revision/Verification Links
Generates secure tokens with expiration for engineer portals
"""
import secrets
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def generate_secure_token(length=32):
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def create_revision_token(conn, request_id, request_type, engineer_email, expiration_days=7):
    """
    Create a revision token for an engineer to revise their rejected request

    Args:
        conn: Database connection
        request_id: Request ID (e.g., REQ-000123)
        request_type: Type of request ('kb_update' or 'new_kb')
        engineer_email: Engineer's email address
        expiration_days: Days until token expires (default: 7)

    Returns:
        str: Secure token
    """
    token = generate_secure_token()
    expires_at = datetime.now() + timedelta(days=expiration_days)

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO revision_tokens (
            token, request_id, request_type, engineer_email,
            action_type, expires_at, created_at, used
        ) VALUES (?, ?, ?, ?, 'revise', ?, GETDATE(), 0)
    ''', (token, request_id, request_type, engineer_email, expires_at.isoformat()))
    conn.commit()

    return token

def create_verification_token(conn, request_id, request_type, engineer_email, kb_link, expiration_days=7):
    """
    Create a verification token for an engineer to verify their approved KB

    Args:
        conn: Database connection
        request_id: Request ID (e.g., REQ-000123)
        request_type: Type of request ('kb_update' or 'new_kb')
        engineer_email: Engineer's email address
        kb_link: Link to the created/updated KB article
        expiration_days: Days until token expires (default: 7)

    Returns:
        str: Secure token
    """
    token = generate_secure_token()
    expires_at = datetime.now() + timedelta(days=expiration_days)

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO revision_tokens (
            token, request_id, request_type, engineer_email,
            action_type, kb_link, expires_at, created_at, used
        ) VALUES (?, ?, ?, ?, 'verify', ?, ?, GETDATE(), 0)
    ''', (token, request_id, request_type, engineer_email, kb_link, expires_at.isoformat()))
    conn.commit()

    return token

def validate_token(conn, token, action_type):
    """
    Validate a token and check if it's expired or already used

    Args:
        conn: Database connection
        token: Token to validate
        action_type: Expected action type ('revise' or 'verify')

    Returns:
        dict: Token data if valid, None if invalid/expired/used
            {
                'request_id': 'REQ-000123',
                'request_type': 'kb_update',
                'engineer_email': 'engineer@example.com',
                'kb_link': 'https://...' (for verify tokens),
                'expires_at': '2024-03-24T...',
                'valid': True
            }
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT request_id, request_type, engineer_email, kb_link,
               expires_at, used, action_type
        FROM revision_tokens
        WHERE token = ?
    ''', (token,))

    row = cursor.fetchone()

    if not row:
        return None  # Token not found

    request_id, request_type, engineer_email, kb_link, expires_at, used, db_action_type = row

    # Check if action type matches
    if db_action_type != action_type:
        return None  # Wrong action type

    # Check if already used
    if used:
        return {
            'valid': False,
            'error': 'Token has already been used',
            'request_id': request_id
        }

    # Check expiration
    expires_datetime = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at
    if datetime.now() > expires_datetime:
        return {
            'valid': False,
            'error': 'Token has expired',
            'request_id': request_id,
            'expired_at': expires_at
        }

    # Token is valid
    return {
        'valid': True,
        'request_id': request_id,
        'request_type': request_type,
        'engineer_email': engineer_email,
        'kb_link': kb_link,
        'expires_at': expires_at
    }

def mark_token_used(conn, token):
    """
    Mark a token as used (cannot be reused)

    Args:
        conn: Database connection
        token: Token to mark as used

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE revision_tokens
            SET used = 1, used_at = GETDATE()
            WHERE token = ?
        ''', (token,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error marking token as used: {e}")
        return False

def get_revision_link(token):
    """
    Generate full revision portal link

    Args:
        token: Revision token

    Returns:
        str: Full URL to revision portal
    """
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    return f"{base_url}/revise/{token}"

def get_verification_link(token):
    """
    Generate full verification portal link

    Args:
        token: Verification token

    Returns:
        str: Full URL to verification portal
    """
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    return f"{base_url}/verify/{token}"

# Example usage
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Token Generator Test")
    print("="*60)

    # Test token generation
    token = generate_secure_token()
    print(f"\nGenerated token: {token}")
    print(f"Token length: {len(token)} characters")

    # Test link generation
    revision_link = get_revision_link(token)
    verification_link = get_verification_link(token)

    print(f"\nRevision link: {revision_link}")
    print(f"Verification link: {verification_link}")

    print("\n" + "="*60)
    print("✅ Token generator working correctly!")
    print("="*60)
