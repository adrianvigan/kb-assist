"""
STANDALONE Engineer Revision Portal
Deploy this as a SEPARATE Streamlit app for engineers only
Engineers should NOT have access to the main dashboard
"""
import streamlit as st
import os
import sys
from datetime import datetime
import psycopg2

def get_connection():
    """Get database connection - read fresh from secrets"""
    try:
        # Get DATABASE_URL from Streamlit secrets
        if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
            DATABASE_URL = st.secrets['DATABASE_URL']
        else:
            st.error("❌ DATABASE_URL not found in secrets!")
            st.info("Please add DATABASE_URL to your Streamlit Cloud app secrets.")
            st.stop()

        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        st.info("Please check your DATABASE_URL secret in Streamlit Cloud settings.")
        st.stop()

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
        st.info(f"🔍 DEBUG: Looking for request_id: {target_request_id}")
    else:
        st.error("❌ Invalid token format")
        st.code(f"Token: {token}")
        st.code(f"Parts: {parts}")
        st.stop()
except Exception as e:
    st.error(f"❌ Invalid revision token: {str(e)}")
    st.stop()

# Look up request by request_id
conn = get_connection()
cursor = conn.cursor()

# First, check if request exists at all (for debugging)
cursor.execute("""
    SELECT request_id, status
    FROM kb_update_requests
    WHERE request_id = %s
    ORDER BY id DESC
    LIMIT 1
""", (target_request_id,))
debug_result = cursor.fetchone()

if debug_result:
    st.info(f"🔍 DEBUG: Found request with status: {debug_result[1]}")
else:
    st.warning("🔍 DEBUG: Request not found in kb_update_requests, checking new_kb_requests...")
    cursor.execute("""
        SELECT request_id, status
        FROM new_kb_requests
        WHERE request_id = %s
        ORDER BY id DESC
        LIMIT 1
    """, (target_request_id,))
    debug_result2 = cursor.fetchone()
    if debug_result2:
        st.info(f"🔍 DEBUG: Found request in new_kb_requests with status: {debug_result2[1]}")

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
    st.caption("Expected status: 'pending follow-up' or 'rejected'")
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

# AI Assistance Section
st.markdown("---")
st.markdown("## 🤖 AI Drafting Assistant")
st.caption("Need help improving your submission? Use the AI tool to generate better content.")

with st.expander("🤖 Generate Improved Content", expanded=False):
    st.markdown("### What would you like to improve?")

    ai_option = st.radio(
        "Select what to improve:",
        ["Enhance PERTS with more detail", "Rewrite issue description", "Generate missing steps", "Improve clarity and structure"],
        key="ai_option"
    )

    if st.button("✨ Generate with AI", key="generate_ai"):
        with st.spinner("🤖 AI is generating improved content..."):
            try:
                # Import AI generator
                import sys
                sys.path.insert(0, os.path.dirname(__file__))
                from dashboard.ai_kb_generator import improve_engineer_submission

                # Map UI option to improvement type
                improvement_map = {
                    "Enhance PERTS with more detail": "enhance",
                    "Rewrite issue description": "rewrite_issue",
                    "Generate missing steps": "generate_missing",
                    "Improve clarity and structure": "improve_clarity"
                }

                improvement_type = improvement_map[ai_option]

                # Generate
                ai_result = improve_engineer_submission(
                    product=product,
                    issue_description=revised_issue or issue_desc or "",
                    troubleshooting_steps=revised_perts or perts or "",
                    manager_feedback=feedback or None,
                    improvement_type=improvement_type
                )

                st.success("✅ AI generation complete!")
                st.markdown("**AI-Generated Improvement:**")
                st.code(ai_result, language="markdown")
                st.info("💡 Copy the content above and paste it into your revision form")

            except Exception as e:
                st.error(f"❌ AI generation failed: {str(e)}")
                st.info("You can still submit your revision manually using the form above")

# Handle form submission
if submit_revision:
    if not revision_notes or not revision_notes.strip():
        st.error("⚠️ Please provide notes explaining your changes")
    else:
        try:
            is_new_kb_request = (report_type == 'no_kb_exists')

            # Generate unique request_id for revision
            # Find next available revision number
            if is_new_kb_request:
                cursor.execute("""
                    SELECT COUNT(*) FROM new_kb_requests
                    WHERE request_id LIKE %s
                """, (f"{request_id}%",))
                revision_count = cursor.fetchone()[0]
                new_request_id = f"{request_id}-R{revision_count}" if revision_count > 1 else request_id
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM kb_update_requests
                    WHERE request_id LIKE %s
                """, (f"{request_id}%",))
                revision_count = cursor.fetchone()[0]
                new_request_id = f"{request_id}-R{revision_count}" if revision_count > 1 else request_id

            if is_new_kb_request:
                # Create revised new_kb_requests entry
                cursor.execute("""
                    INSERT INTO new_kb_requests (
                        request_id, issue_title, product, issue_description,
                        troubleshooting_steps, submitted_by, submitted_date,
                        status, priority, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_request_id,
                    kb_title or revised_issue[:50],
                    product,
                    revised_issue,
                    revised_perts,
                    engineer_name or "Engineer",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'pending',
                    'Medium',
                    f"[REVISION OF {request_id}]\n{revision_notes}\n\n[ORIGINAL FEEDBACK]\n{feedback}"
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
                    new_request_id,
                    kb_id,
                    kb_title,
                    product,
                    revised_issue,
                    revised_perts,
                    engineer_name or "Engineer",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'pending',
                    'Medium',
                    f"[REVISION OF {request_id}]\n{revision_notes}\n\n[ORIGINAL FEEDBACK]\n{feedback}"
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
            st.info(f"Your revision has been submitted as **{new_request_id}** and will be reviewed by the KB team.")
            st.balloons()

            # Prevent resubmission
            st.stop()

        except Exception as e:
            st.error(f"❌ Failed to submit revision: {str(e)}")
            conn.close()

conn.close()
