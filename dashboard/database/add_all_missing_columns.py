"""
Add all missing columns found in SQLite database
"""
from azure_db import get_connection

def add_all_columns():
    """Add all missing columns to match SQLite schema"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Adding missing columns to engineer_reports...")
    try:
        cursor.execute('''
            ALTER TABLE engineer_reports
            ADD COLUMN IF NOT EXISTS product_version VARCHAR(100),
            ADD COLUMN IF NOT EXISTS os VARCHAR(100),
            ADD COLUMN IF NOT EXISTS problem_category VARCHAR(200),
            ADD COLUMN IF NOT EXISTS subcategory VARCHAR(200),
            ADD COLUMN IF NOT EXISTS case_title TEXT,
            ADD COLUMN IF NOT EXISTS case_status VARCHAR(100),
            ADD COLUMN IF NOT EXISTS case_substatus VARCHAR(100),
            ADD COLUMN IF NOT EXISTS kb_audience VARCHAR(100)
        ''')
        conn.commit()
        print("engineer_reports columns added")
    except Exception as e:
        print(f"Note: {e}")
        conn.rollback()

    print("Adding missing columns to kb_update_requests...")
    try:
        cursor.execute('''
            ALTER TABLE kb_update_requests
            ADD COLUMN IF NOT EXISTS case_url VARCHAR(500),
            ADD COLUMN IF NOT EXISTS status_history TEXT,
            ADD COLUMN IF NOT EXISTS kb_audience VARCHAR(100)
        ''')
        conn.commit()
        print("kb_update_requests columns added")
    except Exception as e:
        print(f"Note: {e}")
        conn.rollback()

    print("Adding missing columns to new_kb_requests...")
    try:
        cursor.execute('''
            ALTER TABLE new_kb_requests
            ADD COLUMN IF NOT EXISTS case_url VARCHAR(500),
            ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 1,
            ADD COLUMN IF NOT EXISTS parent_request_id VARCHAR(20),
            ADD COLUMN IF NOT EXISTS original_request_id VARCHAR(20),
            ADD COLUMN IF NOT EXISTS kb_audience VARCHAR(100)
        ''')
        conn.commit()
        print("new_kb_requests columns added")
    except Exception as e:
        print(f"Note: {e}")
        conn.rollback()

    conn.close()
    print("All columns added successfully!")

if __name__ == '__main__':
    add_all_columns()
