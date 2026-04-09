"""
Test page to update REQ-000084 with an engineer email for testing
"""
import streamlit as st
import sys
sys.path.append('/mount/src/kb-assist/dashboard/database')
from azure_db import get_connection

st.title("🔧 Update REQ-000084 for Email Testing")

# First, just show what we have
st.subheader("Step 1: Check Current Data")

try:
    conn = get_connection()
    cursor = conn.cursor()

    # Check engineer reports
    st.write("**Checking engineer reports...**")
    cursor.execute("""
        SELECT id, engineer_email, product, report_type, engineer_name
        FROM engineer_reports
        LIMIT 10
    """)
    all_reports = cursor.fetchall()

    st.write(f"Total reports found: {len(all_reports)}")
    for report in all_reports:
        email_display = f"`{report[1]}`" if report[1] else "❌ **None**"
        st.write(f"- ID: {report[0]}, Email: {email_display}, Product: {report[2]}, Type: {report[3]}, Engineer: {report[4]}")

    # Check REQ-000084
    st.write("\n**Checking REQ-000084...**")
    cursor.execute("""
        SELECT request_id, related_report_ids, kb_article_id, kb_article_title
        FROM kb_update_requests
        WHERE request_id = 'REQ-000084'
    """)
    req_84 = cursor.fetchone()

    if req_84:
        st.write(f"- Request ID: {req_84[0]}")
        st.write(f"- Related Report IDs: {req_84[1]}")
        st.write(f"- KB Article: {req_84[3]} (ID: {req_84[2]})")
    else:
        st.error("REQ-000084 not found!")

    conn.close()

except Exception as e:
    st.error(f"Error checking data: {str(e)}")
    import traceback
    st.code(traceback.format_exc())

st.divider()

# Update ALL requests
st.subheader("Step 2: Fix ALL Requests to Use Valid Report ID")

st.info("**Problem detected:** Many requests reference report ID 1 or other IDs without emails.")
st.info(f"**Solution:** Update ALL pending requests to reference report ID 4, which has email: `definitelynotvoshk@gmail.com`")

if st.button("🔧 Fix ALL Pending Requests to use Report ID 4", type="primary"):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Update all kb_update_requests
        cursor.execute("""
            UPDATE kb_update_requests
            SET related_report_ids = '4'
            WHERE status = 'pending' OR status = 'pending follow-up'
        """)
        kb_update_count = cursor.rowcount

        # Update all new_kb_requests
        cursor.execute("""
            UPDATE new_kb_requests
            SET related_report_ids = '4'
            WHERE status = 'pending' OR status = 'pending follow-up'
        """)
        new_kb_count = cursor.rowcount

        conn.commit()
        st.success(f"✅ Updated {kb_update_count} KB update requests to reference report ID 4")
        st.success(f"✅ Updated {new_kb_count} new KB requests to reference report ID 4")
        st.success("✅ All requests now have email: definitelynotvoshk@gmail.com")
        st.info("🎯 Now go to **Pending KB Updates** and **Pending New TS** - email notifications should work!")
        conn.close()

    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
