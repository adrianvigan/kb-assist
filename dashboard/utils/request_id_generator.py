"""
Request ID Generator for KB Assist
Generates unique request IDs for tracking submissions
Simple sequential format: REQ-001234
"""

def generate_request_id(conn=None):
    """
    Generate unique request ID
    Format: REQ-XXXXXX (6 digits with leading zeros)
    Example: REQ-001234, REQ-001235, etc.

    Args:
        conn: Database connection (optional, for auto-increment)

    Returns:
        String: Request ID in format REQ-XXXXXX
    """
    if conn:
        # Get the highest existing request ID number from database
        cursor = conn.cursor()

        # Try to get max ID from all tables
        try:
            # For Azure SQL
            cursor.execute("""
                SELECT MAX(CAST(SUBSTRING(request_id, 5, 6) AS INT)) as max_id
                FROM (
                    SELECT request_id FROM engineer_reports WHERE request_id LIKE 'REQ-%'
                    UNION
                    SELECT request_id FROM kb_update_requests WHERE request_id LIKE 'REQ-%'
                    UNION
                    SELECT request_id FROM new_kb_requests WHERE request_id LIKE 'REQ-%'
                ) AS all_requests
            """)
            result = cursor.fetchone()
            max_id = result[0] if result and result[0] else 0
        except:
            # For SQLite (simpler syntax)
            try:
                cursor.execute("""
                    SELECT MAX(CAST(SUBSTR(request_id, 5, 6) AS INTEGER)) as max_id
                    FROM (
                        SELECT request_id FROM engineer_reports WHERE request_id LIKE 'REQ-%'
                        UNION
                        SELECT request_id FROM kb_update_requests WHERE request_id LIKE 'REQ-%'
                        UNION
                        SELECT request_id FROM new_kb_requests WHERE request_id LIKE 'REQ-%'
                    )
                """)
                result = cursor.fetchone()
                max_id = result[0] if result and result[0] else 0
            except:
                # Fallback: start from 1
                max_id = 0

        # Increment and format
        next_id = max_id + 1
    else:
        # No connection provided, use timestamp-based fallback
        import time
        next_id = int(time.time()) % 999999

    # Format as REQ-XXXXXX (6 digits with leading zeros)
    return f"REQ-{next_id:06d}"

def validate_request_id(request_id):
    """
    Validate request ID format
    Returns: True if valid, False otherwise
    """
    if not request_id:
        return False

    parts = request_id.split('-')
    if len(parts) != 2:
        return False

    if parts[0] != 'REQ':
        return False

    if not parts[1].isdigit() or len(parts[1]) != 6:
        return False

    return True

def get_next_id_number(conn):
    """
    Get the next available ID number (for display purposes)

    Args:
        conn: Database connection

    Returns:
        int: Next ID number
    """
    cursor = conn.cursor()

    try:
        # For Azure SQL
        cursor.execute("""
            SELECT MAX(CAST(SUBSTRING(request_id, 5, 6) AS INT)) as max_id
            FROM (
                SELECT request_id FROM engineer_reports WHERE request_id LIKE 'REQ-%'
                UNION
                SELECT request_id FROM kb_update_requests WHERE request_id LIKE 'REQ-%'
                UNION
                SELECT request_id FROM new_kb_requests WHERE request_id LIKE 'REQ-%'
            ) AS all_requests
        """)
        result = cursor.fetchone()
        max_id = result[0] if result and result[0] else 0
    except:
        # For SQLite
        try:
            cursor.execute("""
                SELECT MAX(CAST(SUBSTR(request_id, 5, 6) AS INTEGER)) as max_id
                FROM (
                    SELECT request_id FROM engineer_reports WHERE request_id LIKE 'REQ-%'
                    UNION
                    SELECT request_id FROM kb_update_requests WHERE request_id LIKE 'REQ-%'
                    UNION
                    SELECT request_id FROM new_kb_requests WHERE request_id LIKE 'REQ-%'
                )
            """)
            result = cursor.fetchone()
            max_id = result[0] if result and result[0] else 0
        except:
            max_id = 0

    return max_id + 1

if __name__ == '__main__':
    # Test generation (without database connection)
    print("Testing Request ID Generation (no database):")
    for i in range(5):
        req_id = generate_request_id()
        is_valid = validate_request_id(req_id)
        print(f"  {req_id} - Valid: {is_valid}")

    print("\nTesting with simulated sequential IDs:")
    for i in range(1, 6):
        req_id = f"REQ-{i:06d}"
        is_valid = validate_request_id(req_id)
        print(f"  {req_id} - Valid: {is_valid}")
