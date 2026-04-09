"""
Add missing columns to PostgreSQL database
"""
from azure_db import get_connection

def add_columns():
    """Add missing columns to tables"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Adding kb_article_link column to engineer_reports...")
    try:
        cursor.execute('''
            ALTER TABLE engineer_reports
            ADD COLUMN IF NOT EXISTS kb_article_link VARCHAR(500)
        ''')
        conn.commit()
        print("kb_article_link column added successfully")
    except Exception as e:
        print(f"Note: {e}")

    conn.close()
    print("Done!")

if __name__ == '__main__':
    add_columns()
