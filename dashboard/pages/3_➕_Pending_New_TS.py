"""
Pending New Troubleshooting Steps Dashboard
Review new troubleshooting steps that don't have existing KBs
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import secrets
import hashlib

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))
from azure_db import get_connection

st.set_page_config(page_title="Pending New TS", page_icon="➕", layout="wide")

# Database connection (Azure SQL)
def get_db_connection():
    return get_connection()

# Parse PERTS into categories
def parse_perts(perts_text):
    """Parse PERTS text into structured categories"""
    if not perts_text:
        return {}

    categories = {}
    current_category = None
    current_content = []

    for line in perts_text.split('\n'):
        line = line.strip()

        # Check if this is a category header (all caps followed by content or newline)
        if line and line.isupper() and '_' in line:
            # Save previous category
            if current_category:
                categories[current_category] = '\n'.join(current_content).strip()

            # Start new category
            current_category = line
            current_content = []
        elif current_category:
            # Add to current category content
            if line:
                current_content.append(line)

    # Save last category
    if current_category:
        categories[current_category] = '\n'.join(current_content).strip()

    return categories

# Token generation for revision links
def generate_token(request_id, token_type='revision'):
    """Generate secure token for revision/verification links"""
    secret = os.getenv('SECRET_KEY', 'kb-assist-secret-key-change-in-production')
    data = f"{request_id}:{token_type}:{datetime.now().isoformat()}"
    token = secrets.token_urlsafe(32)
    return token

# Header
st.title("➕ Pending New Troubleshooting Steps")
st.caption("New troubleshooting steps that need KB creation")

st.divider()

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    products = [
        'All Products',
        'Trend Micro Scam Check',
        'Maximum Security',
        'ID Protection',
        'Mobile Security',
        'Trend Micro VPN',
        'Cleaner One Pro'
    ]
    selected_product = st.selectbox("Filter by Product", products)

with col2:
    priority_filter = st.selectbox(
        "Priority",
        ["All", "high", "medium", "low"]
    )

with col3:
    status_filter = st.selectbox(
        "Status",
        ["pending", "approved", "in_progress", "completed", "rejected"]
    )

try:
    conn = get_db_connection()

    # Build filters (prefix with table alias to avoid ambiguity)
    filters = [f"nkr.status = '{status_filter}'"]

    if selected_product != 'All Products':
        filters.append(f"nkr.product = '{selected_product}'")

    if priority_filter != 'All':
        filters.append(f"nkr.priority = '{priority_filter}'")

    where_clause = " AND ".join(filters)

    # Get new KB requests with engineer notes
    new_kb_df = pd.read_sql(f"""
        SELECT
            nkr.id,
            nkr.request_id,
            nkr.issue_title,
            nkr.product,
            nkr.issue_description,
            nkr.troubleshooting_steps,
            nkr.submitted_by,
            nkr.submitted_date,
            nkr.priority,
            nkr.frequency_count,
            nkr.status,
            nkr.assigned_to,
            nkr.kb_created_id,
            nkr.notes,
            nkr.related_report_ids,
            nkr.reviewed_by,
            nkr.reviewed_date,
            er_orig.engineer_notes as engineer_notes,
            er.engineer_email,
            nkr.kb_audience
        FROM new_kb_requests nkr
        LEFT JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS TEXT)
        LEFT JOIN new_kb_requests nkr_orig ON nkr.request_id = nkr_orig.request_id AND nkr_orig.id = (
            SELECT MIN(id) FROM new_kb_requests WHERE request_id = nkr.request_id
        )
        LEFT JOIN engineer_reports er_orig ON nkr_orig.related_report_ids = CAST(er_orig.id AS TEXT)
        WHERE {where_clause}
          AND nkr.request_id NOT IN (
              SELECT request_id FROM new_kb_requests WHERE status = 'approved'
          )
        ORDER BY
            nkr.frequency_count DESC,
            CASE nkr.priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            nkr.submitted_date DESC
    """, conn)

    # Metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Pending", len(new_kb_df[new_kb_df['status'] == 'pending']))
    col2.metric("Pending Follow-up", len(new_kb_df[new_kb_df['status'] == 'pending follow-up']))
    col3.metric("High Priority", len(new_kb_df[new_kb_df['priority'] == 'high']))
    col4.metric("In Progress", len(new_kb_df[new_kb_df['status'] == 'in_progress']))
    col5.metric("Completed", len(new_kb_df[new_kb_df['status'] == 'completed']))

    st.divider()

    if len(new_kb_df) > 0:
        st.subheader(f"📋 {status_filter.title()} New KB Requests")

        # Display each request
        for idx, row in new_kb_df.iterrows():
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(row['priority'], '⚪')
            frequency_badge = f"🔥 {row['frequency_count']}x" if row['frequency_count'] > 1 else ""

            # KB Audience indicator
            audience_badge = ""
            if pd.notna(row.get('kb_audience')):
                if row['kb_audience'] == 'internal':
                    audience_badge = " 🔒 [INTERNAL KB]"
                else:
                    audience_badge = " 🌐 [PUBLIC KB]"

            with st.expander(
                f"{priority_emoji} **{row['issue_title']}** ({row['product']}) {frequency_badge} - "
                f"Priority: {row['priority'].upper()}{audience_badge}",
                expanded=(idx < 3 and status_filter == 'pending')
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Parse and display PERTS categories
                    if pd.notna(row['troubleshooting_steps']):
                        perts_categories = parse_perts(row['troubleshooting_steps'])

                        # Display each category separately
                        if 'PROBLEM_DESCRIPTION' in perts_categories:
                            st.markdown("**📝 Problem Description:**")
                            st.info(perts_categories['PROBLEM_DESCRIPTION'])

                        if 'ERROR_MESSAGE' in perts_categories:
                            st.markdown("**⚠️ Error Message:**")
                            error_msg = perts_categories['ERROR_MESSAGE']
                            if error_msg.upper() not in ['N/A', 'NONE', '']:
                                st.error(error_msg)
                            else:
                                st.caption("No error message")

                        if 'ROOT_CAUSE' in perts_categories:
                            st.markdown("**🔍 Root Cause:**")
                            st.warning(perts_categories['ROOT_CAUSE'])

                        if 'TROUBLESHOOTING_STEPS' in perts_categories:
                            st.markdown("**🔧 Troubleshooting Steps:**")
                            st.text_area(
                                "Steps",
                                value=perts_categories['TROUBLESHOOTING_STEPS'],
                                height=150,
                                disabled=True,
                                label_visibility="collapsed",
                                key=f"ts_steps_{row['id']}"
                            )

                        if 'SOLUTION_THAT_WORKED' in perts_categories:
                            st.markdown("**✅ Solution That Worked:**")
                            st.success(perts_categories['SOLUTION_THAT_WORKED'])

                        # Display Engineer's Quick Summary (from original submission)
                        if pd.notna(row.get('engineer_notes')) and row['engineer_notes'].strip():
                            st.markdown("**💡 Engineer's Quick Summary:**")
                            st.markdown(f"""
                            <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; border-radius: 5px; margin: 10px 0;">
                                <p style="margin: 0; font-size: 14px; line-height: 1.6;">{row['engineer_notes']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.caption("⬆️ Engineer's first-hand explanation of the fix")

                        # Display Engineer's Response (if this is a revision)
                        if pd.notna(row['notes']) and '[ENGINEER REVISION NOTES]' in str(row['notes']):
                            notes = row['notes']
                            engineer_revision_notes = None

                            parts = notes.split('[ENGINEER REVISION NOTES]')
                            if len(parts) > 1:
                                revision_notes_section = parts[1]
                                if '[ORIGINAL MANAGER FEEDBACK]' in revision_notes_section:
                                    engineer_revision_notes = revision_notes_section.split('[ORIGINAL MANAGER FEEDBACK]')[0].strip()
                                else:
                                    engineer_revision_notes = revision_notes_section.strip()

                            if engineer_revision_notes:
                                st.markdown("**✏️ Engineer's Response:**")
                                st.markdown(f"""
                                <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; border-radius: 5px; margin: 10px 0;">
                                    <div style="color: #000000; margin: 0; font-size: 14px; line-height: 1.6; white-space: pre-wrap;">{engineer_revision_notes}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                st.caption("⬆️ Engineer's explanation of changes made in this revision")

                        # Show any other categories
                        known_categories = {
                            'PROBLEM_DESCRIPTION', 'ERROR_MESSAGE', 'ROOT_CAUSE',
                            'TROUBLESHOOTING_STEPS', 'SOLUTION_THAT_WORKED'
                        }
                        other_categories = set(perts_categories.keys()) - known_categories
                        for category in other_categories:
                            st.markdown(f"**{category.replace('_', ' ').title()}:**")
                            st.info(perts_categories[category])
                    else:
                        st.info("No troubleshooting information provided")

                    st.markdown("---")

                    # Revision History Section (if revisions exist) - SAME AS KB UPDATES
                    original_req_id = row.get('request_id')
                    current_row_id = row['id']

                    # Query ALL revisions for this request EXCEPT the current one
                    revision_history_query = f"""
                        SELECT
                            nkr.id,
                            nkr.request_id,
                            nkr.issue_title,
                            nkr.issue_description,
                            nkr.troubleshooting_steps,
                            nkr.notes,
                            nkr.submitted_date,
                            nkr.reviewed_by,
                            nkr.reviewed_date,
                            nkr.status,
                            er.engineer_notes
                        FROM new_kb_requests nkr
                        LEFT JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS TEXT)
                        WHERE nkr.request_id = '{original_req_id}'
                        AND nkr.id != {current_row_id}
                        ORDER BY nkr.id ASC
                    """

                    revision_history_df = pd.read_sql_query(revision_history_query, conn)

                    # Show revision history if there are previous versions
                    if len(revision_history_df) > 0:
                        st.markdown(f"**📜 Revision History** ({len(revision_history_df)} previous version{'s' if len(revision_history_df) != 1 else ''})")

                        with st.expander("View all revisions and feedback", expanded=False):
                            # Display each revision
                            for rev_idx, rev_row in revision_history_df.iterrows():
                                # Determine which version this is based on order
                                version_num = rev_idx + 1
                                is_original = (rev_idx == 0)

                                # Build revision label
                                if is_original:
                                    rev_label = "📄 Original Submission"
                                    status_emoji = "🟢" if rev_row['status'] == 'superseded' else "⚪"
                                else:
                                    rev_label = f"✏️ Revision {version_num - 1}"
                                    status_emoji = {
                                        'pending': '🟡',
                                        'approved': '✅',
                                        'superseded': '⏭️',
                                        'pending follow-up': '🔄',
                                        'rejected': '❌'
                                    }.get(rev_row['status'], '⚪')

                                submitted_str = pd.to_datetime(rev_row['submitted_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M') if pd.notna(rev_row['submitted_date']) else "N/A"

                                st.markdown(f"### {status_emoji} {rev_label} - {rev_row['status'].upper()}")
                                st.caption(f"Submitted: {submitted_str}")

                                # Parse notes to extract engineer revision notes and manager feedback
                                if pd.notna(rev_row['notes']):
                                    notes = rev_row['notes']

                                    # Extract engineer revision notes
                                    engineer_revision_notes = None
                                    if '[ENGINEER REVISION NOTES]' in notes:
                                        parts = notes.split('[ENGINEER REVISION NOTES]')
                                        if len(parts) > 1:
                                            revision_notes_section = parts[1]
                                            if '[ORIGINAL MANAGER FEEDBACK]' in revision_notes_section:
                                                engineer_revision_notes = revision_notes_section.split('[ORIGINAL MANAGER FEEDBACK]')[0].strip()
                                            else:
                                                engineer_revision_notes = revision_notes_section.strip()

                                    # Show engineer revision notes if available
                                    if engineer_revision_notes:
                                        st.markdown("**📝 Engineer's Revision Notes:**")
                                        st.markdown(f"""
                                        <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; border-radius: 5px; margin: 10px 0;">
                                            <p style="margin: 0; font-size: 14px; line-height: 1.6; white-space: pre-wrap;">{engineer_revision_notes}</p>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # Show engineer initial notes if available (from engineer_reports table)
                                    if pd.notna(rev_row.get('engineer_notes')) and rev_row['engineer_notes'].strip():
                                        st.markdown("**💡 Engineer's Initial Summary:**")
                                        st.markdown(f"""
                                        <div style="background-color: #e7f3ff; padding: 15px; border-left: 4px solid #1976d2; border-radius: 5px; margin: 10px 0;">
                                            <p style="margin: 0; font-size: 14px; line-height: 1.6;">{rev_row['engineer_notes']}</p>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # Extract manager feedback
                                    feedback_text = None
                                    if '[ORIGINAL MANAGER FEEDBACK]' in notes:
                                        feedback_text = notes.split('[ORIGINAL MANAGER FEEDBACK]')[1].strip()
                                    elif 'GENERAL FEEDBACK:' in notes or 'TECHNICAL ISSUES:' in notes:
                                        feedback_text = notes

                                    if feedback_text and ('GENERAL FEEDBACK:' in feedback_text or 'TECHNICAL ISSUES:' in feedback_text):
                                        st.markdown("**📝 Manager's Feedback:**")
                                        st.markdown(f"""
                                        <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; border-radius: 5px; margin: 10px 0;">
                                            <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; margin: 0; font-size: 12px;">{feedback_text}</pre>
                                        </div>
                                        """, unsafe_allow_html=True)

                                # Show issue description
                                st.markdown("**Issue Description:**")
                                st.info(rev_row['issue_description'] if pd.notna(rev_row['issue_description']) else "N/A")

                                # Show PERTS (compact view)
                                st.markdown("**PERTS / Troubleshooting:**")
                                with st.expander("View PERTS", expanded=False):
                                    st.text_area(
                                        "PERTS",
                                        value=rev_row['troubleshooting_steps'] if pd.notna(rev_row['troubleshooting_steps']) else "N/A",
                                        height=200,
                                        disabled=True,
                                        key=f"rev_perts_{rev_row['id']}_{rev_idx}",
                                        label_visibility="collapsed"
                                    )

                                # Review info
                                if pd.notna(rev_row['reviewed_by']):
                                    reviewed_str = pd.to_datetime(rev_row['reviewed_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M') if pd.notna(rev_row['reviewed_date']) else "N/A"
                                    st.caption(f"**Reviewed by:** {rev_row['reviewed_by']} on {reviewed_str}")

                                if rev_idx < len(revision_history_df) - 1:
                                    st.markdown("---")

                        st.markdown("---")

                    # Get related reports
                    related_reports = pd.read_sql("""
                        SELECT
                            report_date,
                            case_number,
                            engineer_name,
                            new_troubleshooting
                        FROM engineer_reports
                        WHERE product = ?
                        AND report_type = 'no_kb_exists'
                        ORDER BY report_date DESC
                        LIMIT 5
                    """, conn, params=(row['product'],))

                    if len(related_reports) > 0:
                        st.markdown(f"**👥 Related Engineer Reports ({len(related_reports)}):**")
                        st.dataframe(
                            related_reports,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "report_date": "Date",
                                "case_number": "Case #",
                                "engineer_name": "Engineer",
                                "new_troubleshooting": st.column_config.TextColumn("Solution", width="large")
                            }
                        )

                with col2:
                    st.markdown("**📊 Details:**")
                    if pd.notna(row.get('request_id')):
                        st.write(f"**Request ID:** `{row['request_id']}`")

                    st.write(f"**Product:** {row['product']}")
                    st.write(f"**Submitted by:** {row['submitted_by']}")
                    st.write(f"**Date:** {pd.to_datetime(row['submitted_date'], format='ISO8601').strftime('%Y-%m-%d')}")
                    st.write(f"**Priority:** {row['priority'].upper()}")
                    st.write(f"**Frequency:** {row['frequency_count']} reports")
                    st.write(f"**Status:** {row['status'].upper()}")

                    if pd.notna(row['assigned_to']):
                        st.write(f"**Assigned to:** {row['assigned_to']}")

                    if pd.notna(row['kb_created_id']):
                        st.success(f"**KB Created:** {row['kb_created_id']}")

                    # Show review information for approved/rejected items
                    if row['status'] in ['approved', 'rejected'] and pd.notna(row.get('reviewed_by')):
                        st.markdown("---")
                        st.markdown("**📝 Review Info:**")
                        st.write(f"**Reviewed by:** {row['reviewed_by']}")
                        if pd.notna(row.get('reviewed_date')):
                            st.write(f"**Reviewed:** {pd.to_datetime(row['reviewed_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M')}")

                    # Notes removed from sidebar - engineer notes now shown in main content after Solution
                    # if pd.notna(row['notes']):
                    #     st.markdown("**📌 Notes:**")
                    #     st.caption(row['notes'])

                    # Action buttons
                    if row['status'] == 'pending':
                        st.markdown("---")
                        st.markdown("**⚡ Actions:**")

                        # Siebel ID input (required for approve/reject)
                        siebel_id = st.text_input(
                            "Your Siebel ID (required)",
                            key=f"siebel_{row['id']}",
                            placeholder="e.g., adriane",
                            help="Enter your Siebel ID to approve or reject this request"
                        )

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            if st.button("✅ Approve", key=f"approve_{row['id']}", use_container_width=True):
                                if siebel_id and siebel_id.strip():
                                    # Capture values BEFORE dialog
                                    current_row_id = row['id']
                                    current_request_id = row['request_id']
                                    current_related_report_ids = row['related_report_ids']
                                    current_product = row.get('product')
                                    current_issue = row.get('issue_title') or row.get('issue_description')

                                    # Show approval modal
                                    @st.dialog(f"Approve Request {current_request_id}", width="large")
                                    def show_approval_modal():
                                        st.markdown("### ✅ Approve New KB Request")
                                        st.caption("Provide the KB article link to notify the engineer.")

                                        # Initialize session state for this dialog if not exists
                                        if f"kb_link_new_input_{current_row_id}" not in st.session_state:
                                            st.session_state[f"kb_link_new_input_{current_row_id}"] = ""

                                        kb_link = st.text_input(
                                            "KB Article Link (Required)",
                                            value=st.session_state[f"kb_link_new_input_{current_row_id}"],
                                            placeholder="https://helpcenter.trendmicro.com/en-us/article/tmka-XXXXX",
                                            key=f"approve_new_kb_link_{current_row_id}"
                                        )

                                        # Update session state with current input
                                        st.session_state[f"kb_link_new_input_{current_row_id}"] = kb_link

                                        st.divider()

                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button("Cancel", use_container_width=True, key=f"cancel_approve_new_{current_row_id}"):
                                                # Clear session state
                                                if f"kb_link_new_input_{current_row_id}" in st.session_state:
                                                    del st.session_state[f"kb_link_new_input_{current_row_id}"]
                                                st.rerun()
                                        with col2:
                                            submit_btn = st.button("✉️ Send Approval Email", use_container_width=True, type="primary", key=f"submit_approve_new_{current_row_id}")

                                        if submit_btn:
                                            if not kb_link or len(kb_link.strip()) < 10:
                                                st.error("⚠️ Please provide a valid KB article link")
                                            else:
                                                    # Get engineer email
                                                    conn_approve = get_db_connection()
                                                    cursor_approve = conn_approve.cursor()

                                                    # Get engineer email from related report
                                                    if current_related_report_ids:
                                                        report_id = str(current_related_report_ids).split(',')[0]
                                                        cursor_approve.execute("""
                                                            SELECT engineer_email, engineer_name
                                                            FROM engineer_reports
                                                            WHERE id = %s
                                                        """, (report_id,))
                                                        engineer_data = cursor_approve.fetchone()

                                                        if engineer_data:
                                                            engineer_email = engineer_data[0]
                                                            engineer_name = engineer_data[1]

                                                            # Check if email exists
                                                            if not engineer_email:
                                                                st.error("❌ This request has no email address. Please ask the engineer to resubmit with their email.")
                                                                conn_approve.close()
                                                                return

                                                            # Generate verification token
                                                            import sys
                                                            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                                                            from utils.token_generator_simple import generate_token
                                                            from utils.email_sender import send_approval_email

                                                            verification_token = generate_token(current_request_id, 'verification')
                                                            verification_link = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/verify/{verification_token}"

                                                            # Send approval email
                                                            with st.spinner("📧 Sending approval email..."):
                                                                email_result = send_approval_email(
                                                                    request_id=current_request_id,
                                                                    engineer_email=engineer_email,
                                                                    engineer_name=engineer_name,
                                                                    kb_link=kb_link.strip(),
                                                                    product=current_product,
                                                                    issue_title=current_issue,
                                                                    verification_link=verification_link
                                                                )

                                                            if email_result['success']:
                                                                # Update status to approved and store KB link
                                                                cursor_approve.execute("""
                                                                    UPDATE new_kb_requests
                                                                    SET status = 'approved',
                                                                        reviewed_date = %s,
                                                                        reviewed_by = %s,
                                                                        kb_created_id = %s
                                                                    WHERE id = %s
                                                                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), siebel_id.strip(), kb_link.strip(), current_row_id))

                                                                # Close ALL other records with the same request_id (past and future revisions)
                                                                cursor_approve.execute("""
                                                                    UPDATE new_kb_requests
                                                                    SET status = 'closed'
                                                                    WHERE request_id = %s
                                                                      AND id != %s
                                                                """, (current_request_id, current_row_id))

                                                                closed_count = cursor_approve.rowcount
                                                                if closed_count > 0:
                                                                    st.info(f"✅ Auto-closed {closed_count} other revision(s) of {current_request_id}")

                                                                conn_approve.commit()
                                                                conn_approve.close()

                                                                # Show success message
                                                                st.success(f"✅ Approval email sent successfully to {engineer_email}")
                                                                st.info(f"📧 The engineer has been notified about the KB article")
                                                                st.info(f"📋 Status updated to: **Approved** (awaiting verification)")
                                                                st.balloons()

                                                                # Clear session state
                                                                if f"kb_link_new_input_{current_row_id}" in st.session_state:
                                                                    del st.session_state[f"kb_link_new_input_{current_row_id}"]

                                                                # Wait before reloading
                                                                import time
                                                                time.sleep(2)
                                                                st.rerun()
                                                            else:
                                                                st.error(f"❌ Failed to send email: {email_result['message']}")
                                                                conn_approve.close()
                                                        else:
                                                            st.error("❌ Engineer email not found in related report")
                                                            conn_approve.close()
                                                    else:
                                                        st.error("❌ No related report found for this request")

                                    show_approval_modal()
                                else:
                                    st.error("⚠️ Please enter your Siebel ID")

                        with col_b:
                            if st.button("📝 Request Follow-up", key=f"reject_{row['id']}", use_container_width=True):
                                if not siebel_id or not siebel_id.strip():
                                    st.error("⚠️ Please enter your Siebel ID")
                                else:
                                    # Capture values BEFORE dialog
                                    current_row_id = row['id']
                                    current_request_id = row['request_id']
                                    current_related_report_ids = row['related_report_ids']
                                    current_siebel = siebel_id.strip()

                                    # Get engineer info from related report
                                    engineer_email = None
                                    engineer_name = None
                                    if pd.notna(current_related_report_ids):
                                        report_id = str(current_related_report_ids).split(',')[0]
                                        eng_query = pd.read_sql(f"""
                                            SELECT engineer_email, engineer_name
                                            FROM engineer_reports
                                            WHERE id = {report_id}
                                            LIMIT 1
                                        """, conn)
                                        if len(eng_query) > 0:
                                            engineer_email = eng_query.iloc[0]['engineer_email']
                                            engineer_name = eng_query.iloc[0]['engineer_name']

                                    # Show rejection modal
                                    @st.dialog(f"Request Follow-up for {current_request_id}", width="large")
                                    def show_rejection_modal():
                                        st.markdown("### 📝 Provide Structured Feedback")
                                        st.caption("Help the engineer improve their submission by providing specific feedback. They'll be able to revise and resubmit.")

                                        st.markdown("---")
                                        st.caption(f"📧 Engineer will be notified: {engineer_email or 'Unknown'}")

                                        # Initialize session state for feedback fields if not exists
                                        if f"general_feedback_new_{current_row_id}" not in st.session_state:
                                            st.session_state[f"general_feedback_new_{current_row_id}"] = ''
                                        if f"technical_issues_new_{current_row_id}" not in st.session_state:
                                            st.session_state[f"technical_issues_new_{current_row_id}"] = ''
                                        if f"missing_info_new_{current_row_id}" not in st.session_state:
                                            st.session_state[f"missing_info_new_{current_row_id}"] = ''
                                        if f"suggestions_new_{current_row_id}" not in st.session_state:
                                            st.session_state[f"suggestions_new_{current_row_id}"] = ''

                                        # Structured feedback fields
                                        st.markdown("**General Feedback** (Required)")
                                        general_feedback = st.text_area(
                                            "Overall assessment and main concerns",
                                            height=100,
                                            placeholder="Example: The troubleshooting steps need more detail and structure...",
                                            key=f"general_feedback_new_{current_row_id}",
                                            label_visibility="collapsed"
                                        )

                                        st.markdown("**Technical Issues**")
                                        technical_issues = st.text_area(
                                            "Specific technical problems or inaccuracies",
                                            height=80,
                                            placeholder="Example: Missing root cause analysis, unclear error handling...",
                                            key=f"technical_issues_new_{current_row_id}",
                                            label_visibility="collapsed"
                                        )

                                        st.markdown("**Missing Information**")
                                        missing_info = st.text_area(
                                            "What information is missing",
                                            height=80,
                                            placeholder="Example: Need error messages, screenshots, version details...",
                                            key=f"missing_info_new_{current_row_id}",
                                            label_visibility="collapsed"
                                        )

                                        st.markdown("**Suggestions for Improvement**")
                                        suggestions = st.text_area(
                                            "How to improve the submission",
                                            height=80,
                                            placeholder="Example: Add step-by-step instructions, include prerequisites...",
                                            key=f"suggestions_new_{current_row_id}",
                                            label_visibility="collapsed"
                                        )

                                        st.markdown("---")

                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button("Cancel", use_container_width=True, key=f"cancel_reject_new_{current_row_id}"):
                                                # Clear session state
                                                for key in [f"general_feedback_new_{current_row_id}", f"technical_issues_new_{current_row_id}",
                                                           f"missing_info_new_{current_row_id}", f"suggestions_new_{current_row_id}"]:
                                                    if key in st.session_state:
                                                        del st.session_state[key]
                                                st.rerun()
                                        with col2:
                                            submit_reject = st.button("✉️ Send Follow-up Email", use_container_width=True, type="primary", key=f"submit_reject_new_{current_row_id}")

                                        if submit_reject:
                                            if not general_feedback or not general_feedback.strip():
                                                st.error("⚠️ General feedback is required")
                                            else:
                                                # Combine all feedback
                                                feedback_parts = []
                                                if general_feedback:
                                                    feedback_parts.append(f"GENERAL FEEDBACK:\n{general_feedback}")
                                                if technical_issues:
                                                    feedback_parts.append(f"\nTECHNICAL ISSUES:\n{technical_issues}")
                                                if missing_info:
                                                    feedback_parts.append(f"\nMISSING INFORMATION:\n{missing_info}")
                                                if suggestions:
                                                    feedback_parts.append(f"\nSUGGESTIONS FOR IMPROVEMENT:\n{suggestions}")

                                                feedback = "\n".join(feedback_parts)

                                                # Send email if engineer email is available
                                                if engineer_email:
                                                    import sys
                                                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                                                    from utils.email_sender import send_rejection_email

                                                    revision_token = generate_token(current_request_id, 'revision')
                                                    # Link to revision portal (use production URL from env/secrets)
                                                    base_url = os.getenv('BASE_URL', 'http://localhost:8501')
                                                    # For Streamlit Cloud, secrets override env
                                                    try:
                                                        import streamlit as st
                                                        if hasattr(st, 'secrets') and 'BASE_URL' in st.secrets:
                                                            base_url = st.secrets['BASE_URL']
                                                    except:
                                                        pass
                                                    revision_link = f"{base_url}?token={revision_token}"

                                                    with st.spinner("📧 Sending follow-up email..."):
                                                        email_result = send_rejection_email(
                                                            request_id=current_request_id,
                                                            engineer_email=engineer_email,
                                                            engineer_name=engineer_name or "Engineer",
                                                            feedback_text=feedback,
                                                            revision_link=revision_link
                                                        )

                                                    if email_result['success']:
                                                        # Update status to pending follow-up (create fresh connection)
                                                        conn_reject = get_db_connection()
                                                        cursor_reject = conn_reject.cursor()
                                                        cursor_reject.execute("""
                                                            UPDATE new_kb_requests
                                                            SET status = 'pending follow-up',
                                                                reviewed_date = %s,
                                                                reviewed_by = %s,
                                                                notes = %s
                                                            WHERE id = %s
                                                        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_siebel, feedback, current_row_id))
                                                        conn_reject.commit()
                                                        conn_reject.close()

                                                        st.success(f"✅ Email sent successfully to {engineer_email}")
                                                        st.info(f"📧 The engineer has been notified with structured feedback")
                                                        st.info(f"📋 Status updated to: **Pending Follow-up**")
                                                        st.balloons()

                                                        # Clear session state
                                                        for key in [f"general_feedback_new_{current_row_id}", f"technical_issues_new_{current_row_id}",
                                                                   f"missing_info_new_{current_row_id}", f"suggestions_new_{current_row_id}"]:
                                                            if key in st.session_state:
                                                                del st.session_state[key]

                                                        import time
                                                        time.sleep(2)
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Email failed: {email_result.get('error')}")
                                                        st.info("Request not updated. Please fix email issue and try again.")
                                                else:
                                                    # No email - just update status (create fresh connection)
                                                    conn_reject = get_db_connection()
                                                    cursor_reject = conn_reject.cursor()
                                                    cursor_reject.execute("""
                                                        UPDATE new_kb_requests
                                                        SET status = 'pending follow-up',
                                                            reviewed_date = %s,
                                                            reviewed_by = %s,
                                                            notes = %s
                                                        WHERE id = %s
                                                    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_siebel, feedback, current_row_id))
                                                    conn_reject.commit()
                                                    conn_reject.close()

                                                    st.warning(f"⚠️ No engineer email found. Status updated but no email sent.")
                                                    import time
                                                    time.sleep(2)
                                                    st.rerun()

                                    show_rejection_modal()

                        with col_c:
                            if st.button("🤖 AI Draft", key=f"ai_draft_{row['id']}", use_container_width=True):
                                # Get report ID from related_report_ids column
                                if pd.notna(row['related_report_ids']) and str(row['related_report_ids']).strip():
                                    report_id = int(str(row['related_report_ids']).split(',')[0])

                                    # Import and run AI generator
                                    import sys
                                    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                                    from ai_kb_generator import KBGenerator

                                    with st.spinner("🤖 AI is generating KB draft..."):
                                        try:
                                            generator = KBGenerator()
                                            result = generator.generate_kb_draft(report_id)

                                            if result.get('success'):
                                                # Show modal dialog with the draft (no saving)
                                                @st.dialog(f"🤖 AI-Generated KB Draft", width="large")
                                                def show_draft():
                                                    st.markdown(f"### 📝 KB Draft Preview")
                                                    st.caption(f"Tokens used: {result.get('tokens_used', 0)}")
                                                    st.divider()

                                                    # Display title
                                                    st.markdown("#### Title:")
                                                    st.info(result['title'])

                                                    st.divider()

                                                    # Display draft content
                                                    st.markdown("#### Content:")
                                                    st.markdown(result['content'])

                                                    st.divider()

                                                    if st.button("Close", use_container_width=True):
                                                        st.rerun()

                                                show_draft()
                                            else:
                                                st.error(f"❌ Generation failed: {result.get('error')}")
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                                else:
                                    st.warning("No engineer report linked to this KB request")

                        # Reject & Close button (permanently reject without follow-up)
                        st.markdown("---")
                        st.caption("**⚠️ Permanent Rejection:** Use this only if the request is not applicable and should be permanently closed without changes.")
                        if st.button("🚫 Reject & Close (No Follow-up)", key=f"reject_close_{row['id']}", use_container_width=True, type="secondary"):
                            if not siebel_id or not siebel_id.strip():
                                st.error("⚠️ Please enter your Siebel ID first")
                            else:
                                # Capture values for modal
                                current_reject_row_id = row['id']
                                current_reject_request_id = row['request_id']
                                current_reject_siebel = siebel_id.strip()

                                # Show rejection modal
                                @st.dialog(f"⚠️ Permanently Reject {current_reject_request_id}", width="large")
                                def show_permanent_reject_modal():
                                    st.markdown("### 🚫 Permanent Rejection")
                                    st.warning("This will permanently close the request without sending a revision link to the engineer.")

                                    st.markdown("**Reason for Rejection (Required):**")
                                    reject_reason = st.text_area(
                                        "Explain why this request is being permanently rejected",
                                        height=100,
                                        placeholder="Example: Not applicable to this product / Duplicate of REQ-000123 / Out of scope for KB creation",
                                        key=f"permanent_reject_reason_{current_reject_row_id}",
                                        label_visibility="collapsed"
                                    )

                                    st.markdown("---")
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.caption("⚠️ This action cannot be undone")
                                    with col2:
                                        confirm_reject = st.button("🚫 Confirm Rejection", use_container_width=True, type="primary", key=f"confirm_perm_reject_{current_reject_row_id}")

                                    if confirm_reject:
                                        if not reject_reason or not reject_reason.strip():
                                            st.error("⚠️ Please provide a reason for rejection")
                                        else:
                                            # Create NEW database connection
                                            conn_close = get_db_connection()
                                            cursor_close = conn_close.cursor()
                                            cursor_close.execute("""
                                                UPDATE new_kb_requests
                                                SET status = 'rejected',
                                                    reviewed_date = %s,
                                                    reviewed_by = %s,
                                                    notes = %s
                                                WHERE id = %s
                                            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_reject_siebel,
                                                  f"[PERMANENTLY REJECTED]\n{reject_reason}", current_reject_row_id))
                                            conn_close.commit()
                                            conn_close.close()

                                            st.success(f"✅ Request permanently rejected by {current_reject_siebel}")
                                            st.info("📋 Status updated to: **Rejected** (permanently closed)")
                                            st.balloons()

                                            import time
                                            time.sleep(2)
                                            st.rerun()

                                show_permanent_reject_modal()

                    elif row['status'] in ['approved', 'in_progress']:
                        st.markdown("---")
                        st.markdown("**📝 KB Creation:**")

                        kb_id = st.text_input(
                            "KB Article ID (when created)",
                            value=row['kb_created_id'] if pd.notna(row['kb_created_id']) else "",
                            key=f"kb_id_{row['id']}",
                            placeholder="e.g., 000999888"
                        )

                        if st.button("✅ Mark as Completed", key=f"complete_{row['id']}", use_container_width=True):
                            if kb_id:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE new_kb_requests
                                    SET status = 'completed',
                                        kb_created_id = %s
                                    WHERE id = %s
                                """, (kb_id, row['id']))
                                conn.commit()
                                st.success(f"Completed! KB {kb_id} created")
                                st.rerun()
                            else:
                                st.error("Please enter KB Article ID")

                    # Manager's Feedback section (if available)
                    if pd.notna(row['notes']) and row['notes'].strip():
                        st.markdown("---")
                        notes = row['notes']

                        # Extract manager feedback
                        feedback_text = None

                        # Check for revision format with engineer notes
                        if '[ORIGINAL MANAGER FEEDBACK]' in notes:
                            feedback_text = notes.split('[ORIGINAL MANAGER FEEDBACK]')[1].strip()
                        elif 'GENERAL FEEDBACK:' in notes or 'TECHNICAL ISSUES:' in notes:
                            feedback_text = notes

                        # Display manager feedback in yellow box if available
                        if feedback_text and ('GENERAL FEEDBACK:' in feedback_text or 'TECHNICAL ISSUES:' in feedback_text):
                            st.markdown("**📝 Manager's Feedback:**")
                            st.markdown(f"""
                            <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; border-radius: 5px; margin: 10px 0;">
                                <div style="color: #000000; white-space: pre-wrap; font-family: Arial, sans-serif; margin: 0; font-size: 12px;">{feedback_text}</div>
                            </div>
                            """, unsafe_allow_html=True)

                    # Notes section (for admin/manager use - editable)
                    st.markdown("---")
                    with st.expander("📝 Internal Notes (Manager/Admin Only)", expanded=False):
                        # Check if notes contain revision markers - if so, don't pre-fill
                        existing_notes = ""
                        if pd.notna(row['notes']) and '[ENGINEER REVISION NOTES]' not in str(row['notes']) and '[REVISION' not in str(row['notes']):
                            existing_notes = row['notes']

                        notes = st.text_area(
                            "Notes",
                            value=existing_notes,
                            key=f"notes_{row['id']}",
                            height=100,
                            help="Internal notes - not visible to engineers"
                        )

                        if st.button("💾 Save Notes", key=f"save_notes_{row['id']}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE new_kb_requests
                                SET notes = %s
                                WHERE id = %s
                            """, (notes, row['id']))
                            conn.commit()
                            st.success("Notes saved!")
                            st.rerun()

                st.divider()

        # Summary by Product
        if selected_product == 'All Products':
            st.divider()
            st.subheader("📦 Summary by Product")

            product_summary = new_kb_df.groupby('product').agg({
                'id': 'count',
                'frequency_count': 'sum'
            }).reset_index()

            product_summary.columns = ['Product', 'Requests', 'Total Reports']
            product_summary = product_summary.sort_values('Requests', ascending=False)

            st.dataframe(
                product_summary,
                use_container_width=True,
                hide_index=True
            )

    else:
        st.info(f"No {status_filter} new KB requests found for the selected filters")

    conn.close()

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.code(str(e))
