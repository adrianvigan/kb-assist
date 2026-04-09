"""
Test page to update REQ-000084 with an engineer email for testing
"""
import streamlit as st
import sys
sys.path.append('/mount/src/kb-assist/dashboard/database')
from azure_db import get_connection

st.title("🔧 Update REQ-000084 for Email Testing")

if st.button("Update REQ-000084 with Email", type="primary"):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Find engineer reports that have emails
        st.write("Finding engineer reports with emails...")
        cursor.execute("""
            SELECT id, engineer_email, product, issue_description
            FROM engineer_reports
            WHERE engineer_email IS NOT NULL AND engineer_email != ''
            LIMIT 5
        """)
        reports_with_email = cursor.fetchall()

        if reports_with_email:
            st.write("**Engineer reports with emails:**")
            for report in reports_with_email:
                st.write(f"- ID: {report[0]}, Email: {report[1]}, Product: {report[2]}")

            # Use the first one
            report_id = reports_with_email[0][0]
            email = reports_with_email[0][1]

            st.success(f"Using report ID {report_id} with email: {email}")

            # Find REQ-000084
            cursor.execute("""
                SELECT request_id, related_report_ids, kb_article_id, kb_article_title
                FROM kb_update_requests
                WHERE request_id = 'REQ-000084'
            """)
            req_84 = cursor.fetchone()

            if req_84:
                st.write("**Found REQ-000084:**")
                st.write(f"- Current related_report_ids: {req_84[1]}")
                st.write(f"- KB Article: {req_84[3]} (ID: {req_84[2]})")

                # Update to reference the report with email
                cursor.execute("""
                    UPDATE kb_update_requests
                    SET related_report_ids = %s
                    WHERE request_id = 'REQ-000084'
                """, (str(report_id),))

                conn.commit()
                st.success(f"✅ Updated REQ-000084 to reference report ID {report_id}")
                st.success(f"✅ This report has email: {email}")
                st.info("Now go to **Pending KB Updates** page and try the buttons on REQ-000084!")

            else:
                st.error("❌ REQ-000084 not found!")
        else:
            st.error("❌ No engineer reports with emails found!")
            st.write("Checking all engineer reports...")
            cursor.execute("SELECT id, engineer_email FROM engineer_reports LIMIT 10")
            all_reports = cursor.fetchall()
            for report in all_reports:
                st.write(f"- ID: {report[0]}, Email: {report[1]}")

        conn.close()

    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
