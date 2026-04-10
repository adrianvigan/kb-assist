#!/usr/bin/env python3
"""
Force add email to REQ-000060 for testing
"""
import sys
import os

# Add dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))

# Import database connection
from database.azure_db import get_connection

def add_email_to_req60():
    """Add definitelynotvoshk@gmail.com to REQ-000060"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get related_report_ids for REQ-000060
        cursor.execute("""
            SELECT related_report_ids
            FROM new_kb_requests
            WHERE request_id = 'REQ-000060'
        """)

        result = cursor.fetchone()

        if not result:
            print("❌ REQ-000060 not found in new_kb_requests")
            conn.close()
            return False

        related_report_ids = result[0]
        print(f"📋 REQ-000060 found")
        print(f"   related_report_ids: {related_report_ids}")

        if related_report_ids:
            # Parse the ID (could be string or int)
            try:
                report_id = int(related_report_ids)
            except (ValueError, TypeError):
                print(f"⚠️  Could not parse related_report_ids: {related_report_ids}")
                report_id = None

            if report_id:
                # Update existing engineer_reports entry
                cursor.execute("""
                    UPDATE engineer_reports
                    SET engineer_email = %s
                    WHERE id = %s
                    RETURNING id, engineer_name, engineer_email
                """, ('definitelynotvoshk@gmail.com', report_id))

                updated = cursor.fetchone()
                if updated:
                    conn.commit()
                    print(f"\n✅ Updated engineer_reports.id = {updated[0]}")
                    print(f"   Engineer: {updated[1]}")
                    print(f"   Email: {updated[2]}")
                else:
                    print(f"⚠️  No engineer_reports entry found with id={report_id}")
                    print("   Creating new entry...")
                    related_report_ids = None  # Fall through to create new

        if not related_report_ids:
            # Create new engineer_reports entry
            print("\n📝 Creating new engineer_reports entry...")

            cursor.execute("""
                INSERT INTO engineer_reports (
                    case_number, case_title, product, engineer_name,
                    engineer_email, report_type, new_troubleshooting, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                RETURNING id
            """, (
                'TEST-060',
                'Test for REQ-000060',
                'Test Product',
                'Test Engineer',
                'definitelynotvoshk@gmail.com',
                'no_kb_exists',
                'Test troubleshooting steps'
            ))

            new_report_id = cursor.fetchone()[0]

            # Link it to REQ-000060
            cursor.execute("""
                UPDATE new_kb_requests
                SET related_report_ids = %s
                WHERE request_id = 'REQ-000060'
            """, (str(new_report_id),))

            conn.commit()
            print(f"✅ Created engineer_reports.id = {new_report_id}")
            print(f"✅ Linked to REQ-000060")

        # Verify the final state
        print("\n🔍 Verifying...")
        cursor.execute("""
            SELECT
                nkr.request_id,
                nkr.submitted_by,
                nkr.related_report_ids,
                er.engineer_email,
                er.engineer_name
            FROM new_kb_requests nkr
            LEFT JOIN engineer_reports er ON nkr.related_report_ids = er.id::text
            WHERE nkr.request_id = 'REQ-000060'
        """)

        verify = cursor.fetchone()
        if verify:
            print(f"\n✅ Final State:")
            print(f"   Request ID: {verify[0]}")
            print(f"   Submitted By: {verify[1]}")
            print(f"   Related Report ID: {verify[2]}")
            print(f"   Engineer Email: {verify[3]}")
            print(f"   Engineer Name: {verify[4]}")

            if verify[3] == 'definitelynotvoshk@gmail.com':
                print("\n🎉 SUCCESS! Email added to REQ-000060")
                return True
            else:
                print("\n⚠️  Email not showing in JOIN - check data")
                return False
        else:
            print("❌ Verification failed")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = add_email_to_req60()
    sys.exit(0 if success else 1)
