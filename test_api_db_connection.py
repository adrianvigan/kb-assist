"""
Test API server database connection
"""
import sys
import os

# Add database path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard', 'database'))

try:
    from azure_db import get_connection
    print("✅ Successfully imported azure_db")

    conn = get_connection()
    print("✅ Database connection successful")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM engineer_reports")
    count = cursor.fetchone()[0]
    print(f"✅ Engineer reports count: {count}")

    cursor.execute("SELECT COUNT(*) FROM kb_update_requests")
    count = cursor.fetchone()[0]
    print(f"✅ KB update requests count: {count}")

    conn.close()
    print("\n🎉 All database connections working!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
