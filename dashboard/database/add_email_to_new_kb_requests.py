"""
Add submitted_by_email column to new_kb_requests table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from azure_db import get_connection

def add_email_column():
    """Add submitted_by_email column to new_kb_requests"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Adding submitted_by_email column to new_kb_requests...")

        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'new_kb_requests'
            AND COLUMN_NAME = 'submitted_by_email'
        """)

        exists = cursor.fetchone()[0]

        if exists:
            print("✓ Column already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE new_kb_requests
                ADD submitted_by_email NVARCHAR(200)
            """)
            conn.commit()
            print("✅ Column added successfully")

        # Now populate it from engineer_reports where possible
        print("\nPopulating emails from engineer_reports...")
        cursor.execute("""
            UPDATE nkr
            SET submitted_by_email = er.engineer_email
            FROM new_kb_requests nkr
            INNER JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS TEXT)
            WHERE nkr.submitted_by_email IS NULL
            AND er.engineer_email IS NOT NULL
        """)

        updated = cursor.rowcount
        conn.commit()
        print(f"✅ Updated {updated} rows with emails from engineer_reports")

        # Show summary
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN submitted_by_email IS NOT NULL THEN 1 ELSE 0 END) as with_email,
                SUM(CASE WHEN submitted_by_email IS NULL THEN 1 ELSE 0 END) as without_email
            FROM new_kb_requests
        """)

        total, with_email, without_email = cursor.fetchone()
        print(f"\n📊 Summary:")
        print(f"   Total requests: {total}")
        print(f"   With email: {with_email}")
        print(f"   Without email: {without_email}")

        conn.close()
        print("\n✅ Migration complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        conn.close()
        raise

if __name__ == '__main__':
    add_email_column()
