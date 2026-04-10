"""
Update REQ-000064 with email for testing
"""
import sys
sys.path.insert(0, 'dashboard/database')
from azure_db import get_connection

conn = get_connection()
cursor = conn.cursor()

# Find the related_report_ids for REQ-000064
cursor.execute("""
    SELECT id, related_report_ids
    FROM new_kb_requests
    WHERE request_id = 'REQ-000064'
""")

result = cursor.fetchone()
if result:
    nkr_id = result[0]
    related_report_ids = result[1]

    print(f"Found REQ-000064:")
    print(f"  new_kb_requests.id: {nkr_id}")
    print(f"  related_report_ids: {related_report_ids}")

    if related_report_ids:
        report_id = str(related_report_ids).split(',')[0]

        # Update engineer_reports with the email
        cursor.execute("""
            UPDATE engineer_reports
            SET engineer_email = %s
            WHERE id = %s
        """, ('definitelynotvoshk@gmail.com', report_id))

        conn.commit()
        print(f"\n✅ Updated engineer_reports.id={report_id} with email: definitelynotvoshk@gmail.com")
    else:
        print("\n⚠️ No related_report_ids found - creating a dummy engineer_reports entry")

        # Create a minimal engineer_reports entry
        cursor.execute("""
            INSERT INTO engineer_reports (
                case_number, case_title, product, engineer_name,
                engineer_email, report_type, new_troubleshooting, created_at
            ) VALUES (
                'TEST-CASE', 'Test Case for REQ-000064', 'Test Product',
                'Test Engineer', 'definitelynotvoshk@gmail.com',
                'no_kb_exists', 'Test troubleshooting', NOW()
            )
            RETURNING id
        """)

        new_report_id = cursor.fetchone()[0]

        # Update new_kb_requests to link to it
        cursor.execute("""
            UPDATE new_kb_requests
            SET related_report_ids = %s
            WHERE request_id = 'REQ-000064'
        """, (str(new_report_id),))

        conn.commit()
        print(f"✅ Created engineer_reports.id={new_report_id} and linked to REQ-000064")
        print(f"✅ Email set to: definitelynotvoshk@gmail.com")
else:
    print("❌ REQ-000064 not found")

conn.close()
