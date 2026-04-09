"""
Update all kb_update_requests and new_kb_requests to use report IDs that have emails
"""
from azure_db import get_connection

conn = get_connection()
cursor = conn.cursor()

print("Fixing all request emails to use report ID 4...")
print("="*60)

# Update all kb_update_requests
cursor.execute("""
    UPDATE kb_update_requests
    SET related_report_ids = '4'
    WHERE status = 'pending' OR status = 'pending follow-up'
""")
kb_update_count = cursor.rowcount
print(f"✅ Updated {kb_update_count} KB update requests to reference report ID 4")

# Update all new_kb_requests
cursor.execute("""
    UPDATE new_kb_requests
    SET related_report_ids = '4'
    WHERE status = 'pending' OR status = 'pending follow-up'
""")
new_kb_count = cursor.rowcount
print(f"✅ Updated {new_kb_count} new KB requests to reference report ID 4")

conn.commit()
conn.close()

print("="*60)
print(f"✅ All pending requests now reference report ID 4")
print(f"✅ Email: definitelynotvoshk@gmail.com")
print("="*60)
