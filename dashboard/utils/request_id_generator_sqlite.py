"""
Request ID Generator for KB Assist - SQLite Version
Generates unique request IDs for tracking submissions
Simple sequential format: REQ-001234
"""

def generate_request_id(conn=None):
    """
    Generate unique request ID for SQLite
    Format: REQ-XXXXXX (6 digits with leading zeros)

    Args:
        conn: SQLite database connection

    Returns:
        String: Request ID in format REQ-XXXXXX
    """
    if conn:
        cursor = conn.cursor()

        # SQLite syntax - get max request ID from all tables
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
        next_id = max_id + 1
    else:
        # Fallback
        import time
        next_id = int(time.time()) % 999999

    return f"REQ-{next_id:06d}"
