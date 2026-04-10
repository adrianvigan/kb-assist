"""
Add revision tracking columns to new_kb_requests table
This makes it work exactly like kb_update_requests
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from azure_db import get_connection

def add_revision_columns():
    """Add revision_number, original_request_id, parent_request_id to new_kb_requests"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Adding revision tracking columns to new_kb_requests...")

        # Check and add revision_number
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'new_kb_requests'
            AND column_name = 'revision_number'
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE new_kb_requests
                ADD revision_number INT DEFAULT 0
            """)
            print("✅ Added revision_number column")
        else:
            print("✓  revision_number already exists")

        # Check and add original_request_id
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'new_kb_requests'
            AND column_name = 'original_request_id'
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE new_kb_requests
                ADD original_request_id VARCHAR(50)
            """)
            print("✅ Added original_request_id column")
        else:
            print("✓  original_request_id already exists")

        # Check and add parent_request_id
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'new_kb_requests'
            AND column_name = 'parent_request_id'
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE new_kb_requests
                ADD parent_request_id INT
            """)
            print("✅ Added parent_request_id column")
        else:
            print("✓  parent_request_id already exists")

        conn.commit()

        # Initialize existing records (set revision_number = 0, original_request_id = request_id)
        print("\nInitializing existing records...")
        cursor.execute("""
            UPDATE new_kb_requests
            SET revision_number = 0,
                original_request_id = request_id
            WHERE revision_number IS NULL
        """)

        updated = cursor.rowcount
        conn.commit()
        print(f"✅ Initialized {updated} existing records")

        # Show summary
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN revision_number = 0 THEN 1 ELSE 0 END) as originals,
                SUM(CASE WHEN revision_number > 0 THEN 1 ELSE 0 END) as revisions
            FROM new_kb_requests
        """)

        total, originals, revisions = cursor.fetchone()
        print(f"\n📊 Summary:")
        print(f"   Total requests: {total}")
        print(f"   Original submissions: {originals}")
        print(f"   Revisions: {revisions}")

        conn.close()
        print("\n✅ Migration complete!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == '__main__':
    success = add_revision_columns()
    sys.exit(0 if success else 1)
