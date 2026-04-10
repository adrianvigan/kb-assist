"""
Standalone Engineer Revision Portal
This runs separately from the dashboard - engineers access this directly
"""
import streamlit as st
import sqlite3
import os
import sys
from datetime import datetime

st.set_page_config(
    page_title="Revise KB Request",
    page_icon="✏️",
    layout="wide"
)

# Custom CSS to ensure text readability on colored backgrounds
st.markdown("""
<style>
    /* Override Streamlit's dark theme white text for colored backgrounds */
    .st-emotion-cache-467cry pre,
    .st-emotion-cache-acwcvw pre,
    div[style*="background-color: #fff3cd"] pre,
    div[style*="background-color: #e3f2fd"] pre,
    div[style*="background-color: #fff3cd"] p,
    div[style*="background-color: #e3f2fd"] p,
    div[style*="background-color: #fff3cd"] *,
    div[style*="background-color: #e3f2fd"] *,
    div[style*="background-color: #fff3cd"] div,
    div[style*="background-color: #e3f2fd"] div,
    div[style*="background-color: #fff3cd"] strong,
    div[style*="background-color: #e3f2fd"] strong {
        color: #000000 !important;
    }

    /* Target all text elements in colored divs */
    div[style*="background-color: #fff3cd"],
    div[style*="background-color: #e3f2fd"] {
        color: #000000 !important;
    }

    /* Override all Streamlit emotion cache classes within colored backgrounds */
    div[style*="background-color: #fff3cd"] .st-emotion-cache-467cry,
    div[style*="background-color: #e3f2fd"] .st-emotion-cache-467cry,
    div[style*="background-color: #fff3cd"] [class*="st-emotion"],
    div[style*="background-color: #e3f2fd"] [class*="st-emotion"] {
        color: #000000 !important;
    }
</style>

<script>
// Force text color update on page load (JavaScript backup)
setTimeout(function() {
    // Target yellow background divs
    document.querySelectorAll('div[style*="background-color: #fff3cd"]').forEach(function(el) {
        el.style.color = '#000000';
        el.querySelectorAll('*').forEach(function(child) {
            child.style.color = '#000000';
        });
    });

    // Target light blue background divs
    document.querySelectorAll('div[style*="background-color: #e3f2fd"]').forEach(function(el) {
        el.style.color = '#000000';
        el.querySelectorAll('*').forEach(function(child) {
            child.style.color = '#000000';
        });
    });
}, 100);
</script>
""", unsafe_allow_html=True)

def get_db_connection():
    """Get database connection"""
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'kb_assist.db')
    return sqlite3.connect(db_path)

# Get token from URL query params
query_params = st.query_params
token = query_params.get("token", None)

# Handle empty string as None (Streamlit sometimes returns "" instead of None)
if token == "":
    token = None

if not token:
    # Show landing page when no token provided
    st.title("✏️ KB Request Revision Portal")
    st.info("👋 This portal is used to revise KB requests after manager feedback.")
    st.markdown("---")
    st.markdown("### How to use this portal:")
    st.markdown("""
    1. When a manager requests changes to your KB submission, you'll receive an email
    2. Click the **"Revise Submission"** link in the email
    3. The link will bring you here with your submission pre-loaded
    4. Make the requested changes and resubmit
    """)
    st.markdown("---")
    st.warning("⚠️ **No revision token found in URL**")
    st.info("Please use the revision link from your email. If you don't have one, this portal cannot be accessed directly.")
    st.markdown("---")
    st.markdown("**Need help?** Contact your KB manager for assistance.")
    st.stop()

# Look up request by token
conn = get_db_connection()
cursor = conn.cursor()

# First, look up the request_id associated with this token
# Check if the token exists in email_notifications table
cursor.execute("""
    SELECT request_id
    FROM email_notifications
    WHERE revision_link LIKE ?
    ORDER BY sent_at DESC
    LIMIT 1
""", (f'%{token}%',))

token_result = cursor.fetchone()

if not token_result:
    st.error("❌ Invalid or expired revision token")
    st.info("This link may have expired or is invalid. Please contact your KB manager for a new revision link.")
    conn.close()
    st.stop()
    # Fallback in case st.stop() doesn't work (bare mode)
    import sys
    sys.exit(0)

# Defensive check (should never happen after st.stop, but just in case)
if token_result is None:
    st.error("❌ System Error: Token validation failed")
    conn.close()
    import sys
    sys.exit(0)

target_request_id = token_result[0]

# Try kb_update_requests first (KB Updates/Outdated/Missing Steps)
# First check if request exists at all (any status)
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
        er.report_type,
        er.product_version,
        er.os,
        er.engineer_notes,
        ku.kb_audience
    FROM kb_update_requests ku
    LEFT JOIN engineer_reports er ON ku.related_report_ids = CAST(er.id AS TEXT)
    WHERE ku.request_id = ?
    ORDER BY ku.id DESC
    LIMIT 1
""", (target_request_id,))

result = cursor.fetchone()

# If not found in kb_update_requests, try new_kb_requests (New KB Creation)
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
            'no_kb_exists' as report_type,
            NULL as product_version,
            NULL as os,
            er.engineer_notes,
            nkr.kb_audience
        FROM new_kb_requests nkr
        LEFT JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS TEXT)
        WHERE nkr.request_id = ?
        ORDER BY nkr.id DESC
        LIMIT 1
    """, (target_request_id,))

    result = cursor.fetchone()

if not result:
    st.error("❌ Request not found or link has expired")
    st.info("Please contact your KB manager if you believe this is an error.")
    conn.close()
    st.stop()

# Unpack result
(req_id, request_id, kb_id, kb_title, product, issue_desc, feedback,
 kb_link, status, perts, case_number, engineer_name, engineer_email,
 report_type, product_version, os_info, original_engineer_notes, kb_audience) = result

# Check if this request has already been superseded (revision already submitted)
if status == 'superseded':
    st.markdown("""
    <div style="background-color: #d4edda; padding: 20px; border-left: 4px solid #28a745; border-radius: 5px; margin-top: 20px;">
        <h2 style="color: #155724; margin-top: 0;">✅ Already Submitted!</h2>
        <p style="color: #155724; margin: 10px 0;">This revision link has already been used. Your revision has been submitted and is being reviewed by the KB team.</p>
        <hr style="border-color: #c3e6cb;">
        <h4 style="color: #155724;">What's Next?</h4>
        <ul style="color: #155724;">
            <li>Your revision is currently under review</li>
            <li>The KB team will review your updated submission</li>
            <li>You'll receive an email when they approve or provide additional feedback</li>
        </ul>
        <p style="color: #155724; margin: 20px 0 0 0;"><strong>You can close this page. Thank you!</strong></p>
    </div>
    """, unsafe_allow_html=True)
    conn.close()
    st.stop()

# Check if request is in a status that doesn't need revision
if status not in ['pending follow-up', 'rejected']:
    # Request has been approved, pending, or in another status - no revision needed
    st.markdown(f"""
    <div style="background-color: #d4edda; padding: 20px; border-left: 4px solid #28a745; border-radius: 5px; margin-top: 20px;">
        <h2 style="color: #155724; margin-top: 0;">✅ Revision No Longer Needed!</h2>
        <p style="color: #155724; margin: 10px 0;">This request is currently in <strong>{status.upper()}</strong> status and does not require revision.</p>
        <hr style="border-color: #c3e6cb;">
        <h4 style="color: #155724;">What happened?</h4>
        <ul style="color: #155724;">
            <li>Your previous revision has been submitted and processed</li>
            <li>The request is now being reviewed or has been approved</li>
            <li>This revision link is no longer active</li>
        </ul>
        <p style="color: #155724; margin: 20px 0 0 0;"><strong>You can close this page. Thank you!</strong></p>
    </div>
    """, unsafe_allow_html=True)
    conn.close()
    st.stop()

# Page header with Trend Micro colors
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
    <div style="background-color: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; border-radius: 5px; color: #000000;">
        <div style="white-space: pre-wrap; font-family: Arial, sans-serif; margin: 0; color: #000000; line-height: 1.5;">{feedback}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No specific feedback provided")

st.markdown("---")

# Show original submission
with st.expander("📋 View Original Submission", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Product:** {product}")
        st.markdown(f"**Case Number:** {case_number}")
        st.markdown(f"**Report Type:** {report_type}")
    with col2:
        st.markdown(f"**Product Version:** {product_version or 'N/A'}")
        st.markdown(f"**OS:** {os_info or 'N/A'}")

    if kb_link:
        st.markdown(f"**KB Reference:** {kb_link}")

    st.markdown("**Issue Description:**")
    st.info(issue_desc or "N/A")

    # Show original engineer notes if available
    if original_engineer_notes and original_engineer_notes.strip():
        st.markdown("**💡 Engineer's Original Quick Summary:**")
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; border-radius: 5px; margin: 10px 0; color: #000000;">
            <div style="margin: 0; font-size: 14px; line-height: 1.6; color: #000000; font-family: Arial, sans-serif;">{original_engineer_notes}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("**Original PERTS/Troubleshooting:**")
    st.text_area("PERTS", value=perts or "N/A", height=200, disabled=True, key="original_perts")

st.markdown("---")
st.markdown("## ✏️ Update Your Submission")
st.caption("Based on the feedback above, please revise your submission:")

# Revision form
with st.form("revision_form"):
    # Issue description
    revised_issue = st.text_area(
        "Issue Description (Updated)",
        value=issue_desc or "",
        height=100,
        help="Update the issue description if needed"
    )

    # PERTS/Troubleshooting
    revised_perts = st.text_area(
        "Updated PERTS / Troubleshooting Steps",
        value=perts or "",
        height=300,
        help="Update your troubleshooting steps based on manager feedback"
    )

    # HIGHLIGHTED SECTION - Notes for KB team (right after PERTS)
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; border-radius: 5px; margin: 10px 0; color: #000000;">
        <h4 style="margin-top: 0; color: #1976d2; font-family: Arial, sans-serif;">📝 Your Quick Summary (Required)</h4>
        <div style="margin-bottom: 5px; font-size: 14px; color: #000000; font-family: Arial, sans-serif;">
            <strong style="color: #000000;">Explain what you changed and what the actual fix was.</strong> This helps the KB team understand your revision.
        </div>
    </div>
    """, unsafe_allow_html=True)

    revision_notes = st.text_area(
        "Revision Notes",
        height=120,
        placeholder=f"Example: I've addressed the feedback by adding more details about the root cause. The actual issue was that customer's SSL certificate was expired. I added specific steps to check certificate validity and how to resolve it. Also included the exact error message customers see.",
        help="Explain what changes you made based on the manager's feedback",
        label_visibility="collapsed"
    )
    st.markdown("---")

    # KB link if applicable
    revised_kb_link = st.text_input(
        "KB Article Reference (if applicable)",
        value=kb_link or "",
        help="Link to the KB article you're updating"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        st.info(f"💡 **Tip:** Your revision will create a new request that references {request_id}")

    with col2:
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
            # Determine which table we're working with
            is_new_kb_request = (report_type == 'no_kb_exists')

            if is_new_kb_request:
                # Handle new_kb_requests revision (SAME AS KB UPDATE REQUESTS)
                # Get parent request details to track revision chain
                cursor.execute("""
                    SELECT
                        original_request_id,
                        revision_number
                    FROM new_kb_requests
                    WHERE id = ?
                """, (req_id,))
                parent_data = cursor.fetchone()

                if not parent_data:
                    st.error("❌ Parent request not found")
                    st.stop()

                # Determine original_request_id and new revision number
                if parent_data[0]:
                    # This is already a revision, use same original
                    original_req_id = parent_data[0]
                    new_revision_number = (parent_data[1] or 0) + 1
                else:
                    # This is the first revision of an original request
                    original_req_id = request_id
                    new_revision_number = 1

                # Create a new engineer_reports entry if engineer submitted PERTS
                if revised_perts and revised_perts.strip():
                    cursor.execute("""
                        INSERT INTO engineer_reports (
                            report_date, case_title, case_status, case_substatus,
                            product, report_type, new_troubleshooting,
                            engineer_name, engineer_email, status, request_id, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        datetime.now().isoformat(),
                        revised_issue,
                        'Closed',
                        'Resolved',
                        product,
                        'no_kb_exists',
                        revised_perts,
                        engineer_name,
                        engineer_email,
                        'pending',
                        request_id,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    new_report_id = cursor.lastrowid
                else:
                    new_report_id = None

                # Create revised new_kb_requests entry
                cursor.execute("""
                    INSERT INTO new_kb_requests (
                        request_id,
                        original_request_id,
                        revision_number,
                        parent_request_id,
                        issue_title,
                        product,
                        issue_description,
                        troubleshooting_steps,
                        submitted_by,
                        submitted_date,
                        status,
                        priority,
                        frequency_count,
                        related_report_ids,
                        notes,
                        kb_audience
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    original_req_id,  # Same request ID as original
                    original_req_id,  # Track original
                    new_revision_number,  # Increment revision number
                    req_id,  # Parent request ID (the one being revised)
                    kb_title or revised_issue[:50],  # Use first 50 chars as title
                    product,
                    revised_issue,
                    revised_perts,
                    engineer_name or "Engineer",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'pending',
                    'Medium',
                    1,
                    str(new_report_id) if new_report_id else None,
                    f"[REVISION {new_revision_number}]\n[ENGINEER REVISION NOTES]\n{revision_notes}\n\n[ORIGINAL MANAGER FEEDBACK]\n{feedback}",
                    kb_audience  # Preserve KB audience from original
                ))

                # Mark parent as superseded
                cursor.execute("""
                    UPDATE new_kb_requests
                    SET status = 'superseded',
                        notes = ?
                    WHERE id = ?
                """, (f"[SUPERSEDED BY REVISION {new_revision_number}]\n[ENGINEER REVISION NOTES]\n{revision_notes}\n\n[ORIGINAL MANAGER FEEDBACK]\n{feedback}", req_id))

                # Commit changes for new_kb_requests revision
                conn.commit()
                conn.close()

                # Set session state to trigger success page
                st.session_state.revision_submitted = True
                st.session_state.submitted_request_id = original_req_id
                st.session_state.submitted_revision_number = new_revision_number
                st.rerun()

            else:
                # Handle kb_update_requests revision (existing code)
                # Get parent request details to track revision chain
                cursor.execute("""
                    SELECT
                        original_request_id,
                        revision_number
                    FROM kb_update_requests
                    WHERE id = ?
                """, (req_id,))

                parent_data = cursor.fetchone()

                # Determine original_request_id and new revision number
                if parent_data and parent_data[0]:
                    # This is already a revision, use same original
                    original_req_id = parent_data[0]
                    new_revision_number = (parent_data[1] or 0) + 1
                else:
                    # This is the first revision of an original request
                    original_req_id = request_id
                    new_revision_number = 1

            # Create a new engineer_reports entry for the revision
            cursor.execute("""
                INSERT INTO engineer_reports (
                    report_date, case_number, case_title, case_status, case_substatus,
                    product, product_version, os, problem_category, subcategory,
                    kb_article_link, report_type, new_troubleshooting,
                    engineer_name, engineer_email, status, request_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                case_number,
                revised_issue,
                'Closed',  # Original case status
                'Resolved',
                product,
                product_version,
                os_info,
                None,  # problem_category
                None,  # subcategory
                revised_kb_link,
                report_type,
                revised_perts,
                engineer_name,
                engineer_email,
                'pending',
                original_req_id,  # Keep same original request ID
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            new_report_id = cursor.lastrowid

            # Create a new kb_update_requests entry for the revision (so it shows in dashboard)
            cursor.execute("""
                INSERT INTO kb_update_requests (
                    request_id,
                    original_request_id,
                    revision_number,
                    parent_request_id,
                    kb_article_id,
                    kb_article_title,
                    product,
                    issue_description,
                    new_troubleshooting,
                    submitted_by,
                    submitted_date,
                    status,
                    priority,
                    related_report_ids,
                    notes,
                    kb_audience
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                original_req_id,  # Same request ID as original
                original_req_id,  # Track original
                new_revision_number,  # Increment revision number
                req_id,  # Parent request ID (the one being revised)
                kb_id,
                kb_title,
                product,
                revised_issue,
                revised_perts,
                engineer_name,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pending',  # Start as pending for KB team review
                'Medium',
                str(new_report_id),  # Link to the new engineer_reports entry
                f"[REVISION {new_revision_number}]\n[ENGINEER REVISION NOTES]\n{revision_notes}\n\n[ORIGINAL MANAGER FEEDBACK]\n{feedback}",
                kb_audience  # Preserve KB audience from original
            ))

            # Update parent request status to 'superseded' (not 'revised')
            cursor.execute("""
                UPDATE kb_update_requests
                SET status = 'superseded',
                    notes = ?
                WHERE id = ?
            """, (f"[SUPERSEDED BY REVISION {new_revision_number}]\n[ENGINEER REVISION NOTES]\n{revision_notes}\n\n[ORIGINAL MANAGER FEEDBACK]\n{feedback}", req_id))

            conn.commit()
            conn.close()

            # Set session state to trigger success page
            st.session_state.revision_submitted = True
            st.session_state.submitted_request_id = original_req_id
            st.session_state.submitted_revision_number = new_revision_number
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to submit revision: {str(e)}")
            st.code(str(e))
            conn.close()

# Check if revision was just submitted
if 'revision_submitted' in st.session_state and st.session_state.revision_submitted:
    st.balloons()

    # Use Streamlit's native HTML component to show success and auto-close
    import streamlit.components.v1 as components
    components.html("""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta http-equiv="refresh" content="3;url=about:blank">
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                        }
                        .success-box {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            text-align: center;
                            max-width: 600px;
                        }
                        h1 { color: #155724; margin-top: 0; }
                        .checkmark {
                            font-size: 64px;
                            color: #28a745;
                            animation: scaleIn 0.5s ease-in-out;
                        }
                        @keyframes scaleIn {
                            0% { transform: scale(0); }
                            50% { transform: scale(1.2); }
                            100% { transform: scale(1); }
                        }
                        .countdown {
                            font-size: 18px;
                            color: #155724;
                            margin-top: 20px;
                            font-weight: bold;
                        }
                    </style>
                </head>
                <body>
                    <div class="success-box">
                        <div class="checkmark">✅</div>
                        <h1>Submission Complete!</h1>
                        <p style="color: #155724; font-size: 16px;">Your revision has been submitted successfully.</p>
                        <p style="color: #666; margin: 20px 0;">
                            <strong>Request ID:</strong> """ + f"{st.session_state.submitted_request_id}" + """ (Revision """ + f"{st.session_state.submitted_revision_number}" + """)
                        </p>
                        <hr style="border-color: #c3e6cb; margin: 20px 0;">
                        <p style="color: #155724;">
                            ✓ Your revision has been saved<br>
                            ✓ KB team has been notified<br>
                            ✓ You'll receive an email with updates
                        </p>
                        <div class="countdown" id="countdown">Closing window in 3 seconds...</div>
                        <button id="closeBtn" style="display: none; margin-top: 20px; padding: 12px 30px; font-size: 16px; background: #d71921; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                            ✕ Close This Tab
                        </button>
                    </div>
                    <script>
                        let seconds = 3;
                        const countdownEl = document.getElementById('countdown');
                        const closeBtn = document.getElementById('closeBtn');

                        const timer = setInterval(() => {
                            seconds--;
                            if (seconds > 0) {
                                countdownEl.textContent = `Closing in ${seconds}...`;
                            } else {
                                clearInterval(timer);

                                // Try to close the window
                                window.close();

                                // Show close button immediately (in case auto-close fails)
                                setTimeout(() => {
                                    countdownEl.innerHTML = '✅ <strong style="font-size: 20px;">You can close this tab now</strong>';
                                    closeBtn.style.display = 'inline-block';
                                }, 200);
                            }
                        }, 1000);

                        // Close button click handler
                        closeBtn.addEventListener('click', () => {
                            window.close();
                            // If still open after click, show Alt+F4 hint
                            setTimeout(() => {
                                countdownEl.innerHTML = '💡 Press <strong>Alt+F4</strong> or <strong>Ctrl+W</strong> to close';
                            }, 300);
                        });
                    </script>
                </body>
                </html>
            """, height=600, scrolling=False)

    st.stop()  # Stop rendering the rest of the page

conn.close()
