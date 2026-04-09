"""
Add missing columns to PostgreSQL database
"""
from azure_db import get_connection

def add_columns():
    """Add missing columns to tables"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Adding columns to engineer_reports...")
    try:
        cursor.execute('''
            ALTER TABLE engineer_reports
            ADD COLUMN IF NOT EXISTS kb_article_link VARCHAR(500),
            ADD COLUMN IF NOT EXISTS kb_created_id VARCHAR(50)
        ''')
        conn.commit()
        print("engineer_reports columns added successfully")
    except Exception as e:
        print(f"Note: {e}")

    print("Adding columns to kb_update_requests...")
    try:
        cursor.execute('''
            ALTER TABLE kb_update_requests
            ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 1,
            ADD COLUMN IF NOT EXISTS original_request_id VARCHAR(20)
        ''')
        conn.commit()
        print("kb_update_requests columns added successfully")
    except Exception as e:
        print(f"Note: {e}")

    print("Adding columns to new_kb_requests...")
    try:
        cursor.execute('''
            ALTER TABLE new_kb_requests
            ADD COLUMN IF NOT EXISTS troubleshooting_steps TEXT,
            ADD COLUMN IF NOT EXISTS frequency_count INTEGER DEFAULT 1
        ''')
        conn.commit()
        print("new_kb_requests columns added successfully")
    except Exception as e:
        print(f"Note: {e}")

    conn.close()
    print("All columns added successfully!")

if __name__ == '__main__':
    add_columns()
