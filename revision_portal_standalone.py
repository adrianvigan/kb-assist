"""
STANDALONE Engineer Revision Portal
Deploy this as a SEPARATE Streamlit app for engineers only
Engineers should NOT have access to the main dashboard
"""
import streamlit as st
import os
import sys
from datetime import datetime

# Add database path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard', 'database'))
from azure_db import get_connection

st.set_page_config(
    page_title="Revise KB Request",
    page_icon="✏️",
    layout="wide"
)

# Get token from URL query params
query_params = st.query_params
token = query_params.get("token", None)

if not token or token == "":
    st.title("✏️ KB Request Revision Portal")
    st.info("👋 This portal is used to revise KB requests after manager feedback.")
    st.markdown("---")
    st.warning("⚠️ **No revision token found in URL**")
    st.info("Please use the revision link from your email.")
    st.stop()

# Extract request_id from token
# Token format: revision_{request_id}_{timestamp}
try:
    parts = token.split('_')
    if len(parts) >= 2 and parts[0] == 'revision':
        target_request_id = parts[1]
    else:
        st.error("❌ Invalid token format")
        st.stop()
except:
    st.error("❌ Invalid revision token")
    st.stop()

# Look up request by request_id
conn = get_connection()
cursor = conn.cursor()

# Try kb_update_requests first
cursor.execute("""
    SELECT
        ku.id,
        ku.request_id,
        ku.kb_article_id,
        ku.kb_article_title,
        ku.product,
        ku.issue_description,
        ku.notes,
        er.kb_article_link,
        ku.status,
        er.new_troubleshooting,
        er.case_number,
        er.engineer_name,
        er.engineer_email,
        er.report_type
    FROM kb_update_requests ku
    LEFT JOIN engineer_reports er ON ku.related_report_ids = CAST(er.id AS TEXT)
    WHERE ku.request_id = %s
      AND ku.status IN ('pending follow-up', 'rejected')
    ORDER BY ku.id DESC
    LIMIT 1
""", (target_request_id,))

result = cursor.fetchone()

# If not found in kb_update_requests, try new_kb_requests
if not result:
    cursor.execute("""
        SELECT
            nkr.id,
            nkr.request_id,
            NULL as kb_article_id,
            nkr.issue_title,
            nkr.product,
            nkr.issue_description,
            nkr.notes,
            NULL as kb_article_link,
            nkr.status,
            nkr.troubleshooting_steps,
            NULL as case_number,
            er.engineer_name,
            er.engineer_email,
            'no_kb_exists' as report_type
        FROM new_kb_requests nkr
        LEFT JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS TEXT)
        WHERE nkr.request_id = %s
          AND nkr.status IN ('pending follow-up', 'rejected')
        ORDER BY nkr.id DESC
        LIMIT 1
    """, (target_request_id,))

    result = cursor.fetchone()

if not result:
    st.error("❌ Request not found or revision link has expired")
    st.info("This request may have already been revised or approved. Please contact your KB manager if you believe this is an error.")
    conn.close()
    st.stop()

# Unpack result
(req_id, request_id, kb_id, kb_title, product, issue_desc, feedback,
 kb_link, status, perts, case_number, engineer_name, engineer_email,
 report_type) = result

# Page header
st.markdown("""
    <div style="background-color: #d71921; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0;">✏️ Revise Your KB Request</h1>
        <p style="color: white; margin: 5px 0 0 0;">Engineer Revision Portal</p>
    </div>
""", unsafe_allow_html=True)

st.caption(f"Request ID: **{request_id}** | Status: **{status}** | Engineer: **{engineer_name}**")

# Show manager feedback
st.markdown("---")
st.markdown("## 📝 Manager's Feedback")
if feedback:
    st.markdown(f"""
    <div style="background-color: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; border-radius: 5px;">
        <div style="white-space: pre-wrap; font-family: Arial, sans-serif;">{feedback}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No specific feedback provided")

st.markdown("---")
st.markdown("## ✏️ Update Your Submission")

# Revision form
with st.form("revision_form"):
    revised_issue = st.text_area(
        "Issue Description (Updated)",
        value=issue_desc or "",
        height=100
    )

    revised_perts = st.text_area(
        "Updated PERTS / Troubleshooting Steps",
        value=perts or "",
        height=300
    )

    st.markdown("---")
    st.markdown("**📝 Your Quick Summary (Required)**")
    st.caption("Explain what you changed and what the actual fix was.")

    revision_notes = st.text_area(
        "Revision Notes",
        height=120,
        placeholder="Example: I've addressed the feedback by adding more details about the root cause. The actual issue was...",
        label_visibility="collapsed"
    )
    st.markdown("---")

    submit_revision = st.form_submit_button("📤 Submit Revision", use_container_width=True, type="primary")

# Handle form submission
if submit_revision:
    if not revision_notes or not revision_notes.strip():
        st.error("⚠️ Please provide notes explaining your changes")
    else:
        try:
            is_new_kb_request = (report_type == 'no_kb_exists')

            if is_new_kb_request:
                # Create revised new_kb_requests entry
                cursor.execute("""
                    INSERT INTO new_kb_requests (
                        request_id, issue_title, product, issue_description,
                        troubleshooting_steps, submitted_by, submitted_date,
                        status, priority, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    request_id,
                    kb_title or revised_issue[:50],
                    product,
                    revised_issue,
                    revised_perts,
                    engineer_name or "Engineer",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'pending',
                    'Medium',
                    f"[REVISION]\n{revision_notes}\n\n[ORIGINAL FEEDBACK]\n{feedback}"
                ))

                # Mark parent as superseded
                cursor.execute("""
                    UPDATE new_kb_requests
                    SET status = 'superseded'
                    WHERE id = %s
                """, (req_id,))
            else:
                # Create revised kb_update_requests entry
                cursor.execute("""
                    INSERT INTO kb_update_requests (
                        request_id, kb_article_id, kb_article_title, product,
                        issue_description, new_troubleshooting, submitted_by,
                        submitted_date, status, priority, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    request_id,
                    kb_id,
                    kb_title,
                    product,
                    revised_issue,
                    revised_perts,
                    engineer_name or "Engineer",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'pending',
                    'Medium',
                    f"[REVISION]\n{revision_notes}\n\n[ORIGINAL FEEDBACK]\n{feedback}"
                ))

                # Mark parent as superseded
                cursor.execute("""
                    UPDATE kb_update_requests
                    SET status = 'superseded'
                    WHERE id = %s
                """, (req_id,))

            conn.commit()
            conn.close()

            # Success message
            st.success("✅ Revision submitted successfully!")
            st.info("Your revision has been submitted and will be reviewed by the KB team.")
            st.balloons()

            # Prevent resubmission
            st.stop()

        except Exception as e:
            st.error(f"❌ Failed to submit revision: {str(e)}")
            conn.close()

conn.close()
