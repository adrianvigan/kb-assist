"""
Pending KB Updates Dashboard
Review and approve KB updates where engineers found outdated information
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))
from azure_db import get_connection

st.set_page_config(page_title="Pending KB Updates", page_icon="⏳", layout="wide")

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

# Header
st.title("⏳ Pending KB Updates")
st.caption("Review KBs that need updating based on engineer field reports")

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
        ["pending", "approved", "rejected", "closed"]
    )

try:
    conn = get_db_connection()

    # Build filters (prefix with kbu. to avoid ambiguity with joined table)
    filters = [f"kbu.status = '{status_filter}'"]

    if selected_product != 'All Products':
        filters.append(f"kbu.product = '{selected_product}'")

    if priority_filter != 'All':
        filters.append(f"kbu.priority = '{priority_filter}'")

    where_clause = " AND ".join(filters)

    # Get pending updates - JOIN with engineer_reports to get report_type
    updates_df = pd.read_sql(f"""
        SELECT
            kbu.id,
            kbu.request_id,
            kbu.original_request_id,
            kbu.revision_number,
            kbu.parent_request_id,
            kbu.kb_article_id,
            kbu.kb_article_title,
            kbu.product,
            kbu.issue_description,
            kbu.new_troubleshooting,
            kbu.submitted_by,
            kbu.submitted_date,
            kbu.priority,
            kbu.status,
            kbu.notes,
            kbu.related_report_ids,
            kbu.reviewed_by,
            kbu.reviewed_date,
            kbu.approved_kb_link,
            er.report_type,
            er_orig.engineer_notes as engineer_notes,
            er.engineer_email,
            kbu.kb_audience
        FROM kb_update_requests kbu
        LEFT JOIN engineer_reports er ON kbu.related_report_ids = CAST(er.id AS TEXT)
        LEFT JOIN kb_update_requests kbu_orig ON kbu.request_id = kbu_orig.request_id AND kbu_orig.revision_number = 0
        LEFT JOIN engineer_reports er_orig ON kbu_orig.related_report_ids = CAST(er_orig.id AS TEXT)
        WHERE {where_clause}
          AND kbu.status NOT IN ('superseded', 'approved', 'closed')
          AND kbu.request_id NOT IN (
              SELECT request_id FROM kb_update_requests WHERE status = 'approved'
          )
          AND er.engineer_email IS NOT NULL
        ORDER BY
            CASE kbu.priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            kbu.submitted_date DESC
    """, conn)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Pending", len(updates_df[updates_df['status'] == 'pending']))
    col2.metric("Pending Follow-up", len(updates_df[updates_df['status'] == 'pending follow-up']))
    col3.metric("Approved", len(updates_df[updates_df['status'] == 'approved']))
    col4.metric("Closed", len(updates_df[updates_df['status'] == 'closed']))

    st.divider()

    if len(updates_df) > 0:
        st.subheader(f"📋 {status_filter.title()} KB Update Requests")

        # Display each update request
        for idx, row in updates_df.iterrows():
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(row['priority'], '⚪')

            # Build title with revision indicator
            revision_indicator = ""
            if pd.notna(row.get('revision_number')) and row['revision_number'] > 0:
                revision_indicator = f" [Revision {int(row['revision_number'])}]"

            # KB Audience indicator
            audience_badge = ""
            if pd.notna(row.get('kb_audience')):
                if row['kb_audience'] == 'internal':
                    audience_badge = " 🔒 [INTERNAL KB]"
                else:
                    audience_badge = " 🌐 [PUBLIC KB]"

            with st.expander(
                f"{priority_emoji} **KB-{row['kb_article_id']}**: {row['kb_article_title']} "
                f"({row['product']}) - Priority: {row['priority'].upper()}{revision_indicator}{audience_badge}",
                expanded=(idx < 3 and status_filter == 'pending')  # Expand first 3 if pending
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Section 1: Current KB Article
                    if pd.notna(row['kb_article_id']):
                        st.markdown("### 📄 Current KB Article")

                        # Fetch full KB data
                        kb_full = pd.read_sql_query(f"""
                            SELECT kb_number, title, content, last_updated, product, category, url
                            FROM kb_articles
                            WHERE kb_number = '{row['kb_article_id']}'
                            LIMIT 1
                        """, conn)

                        if len(kb_full) > 0:
                            kb = kb_full.iloc[0]

                            # KB Header with clickable KB number
                            kb_url = kb['url'] if pd.notna(kb['url']) else f"https://helpcenter.trendmicro.com/en-us/article/tmka-{kb['kb_number']}"
                            st.markdown(f"**[KB-{kb['kb_number']}]({kb_url})**: {kb['title']}")
                            st.caption(f"Product: {kb['product']} | Category: {kb['category']}")

                            # Last Updated
                            if pd.notna(kb['last_updated']):
                                last_updated = pd.to_datetime(kb['last_updated'])
                                days_old = (datetime.now() - last_updated).days
                                st.caption(f"📅 Last Updated: {last_updated.strftime('%Y-%m-%d')} ({days_old} days ago)")

                            # KB Content
                            with st.expander("📖 View Current KB Content", expanded=False):
                                # Parse and format KB content to look like actual KB article
                                import re

                                # Strip HTML tags but preserve structure
                                content_clean = kb['content']

                                # Convert HTML headings to markdown
                                content_clean = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', content_clean, flags=re.IGNORECASE)

                                # Convert lists
                                content_clean = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', content_clean, flags=re.IGNORECASE | re.DOTALL)
                                content_clean = re.sub(r'<ul[^>]*>|</ul>|<ol[^>]*>|</ol>', '', content_clean, flags=re.IGNORECASE)

                                # Convert bold and italic
                                content_clean = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content_clean, flags=re.IGNORECASE)

                                # Convert paragraphs and breaks
                                content_clean = re.sub(r'<br\s*/?>', '\n', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'<p[^>]*>', '\n', content_clean, flags=re.IGNORECASE)
                                content_clean = re.sub(r'</p>', '\n', content_clean, flags=re.IGNORECASE)

                                # Remove remaining HTML tags
                                content_clean = re.sub(r'<[^>]+>', '', content_clean)

                                # Clean up whitespace
                                content_clean = re.sub(r'\n\s*\n\s*\n+', '\n\n', content_clean)  # Max 2 newlines
                                content_clean = content_clean.strip()

                                # Display as formatted markdown in a container
                                st.markdown(
                                    f"""
                                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #0066cc; max-height: 500px; overflow-y: auto;">
                                        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6;">
                                            {content_clean.replace(chr(10), '<br>')}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                        else:
                            st.warning(f"⚠️ KB {row['kb_article_id']} not found in database")

                    st.markdown("---")

                    # Section 2: Engineer's Proposed Changes
                    st.markdown("### ✏️ Engineer's Proposed Changes")

                    # Parse and display PERTS categories (matching Pending New TS format exactly)
                    if pd.notna(row['new_troubleshooting']):
                        perts_categories = parse_perts(row['new_troubleshooting'])

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

                    # Revision History Section (if revisions exist)
                    original_req_id = row.get('original_request_id') or row['request_id']
                    current_row_id = row['id']

                    # Query ALL revisions for this request EXCEPT the current one (which is already displayed above)
                    revision_history_query = f"""
                        SELECT
                            kbu.id,
                            kbu.request_id,
                            kbu.revision_number,
                            kbu.status,
                            kbu.issue_description,
                            kbu.new_troubleshooting,
                            kbu.notes,
                            kbu.submitted_date,
                            kbu.reviewed_by,
                            kbu.reviewed_date,
                            er.kb_article_link,
                            er.engineer_notes
                        FROM kb_update_requests kbu
                        LEFT JOIN engineer_reports er ON kbu.related_report_ids = CAST(er.id AS TEXT)
                        WHERE (kbu.request_id = '{original_req_id}' OR kbu.original_request_id = '{original_req_id}')
                        AND kbu.id != {current_row_id}
                        ORDER BY kbu.revision_number ASC, kbu.id ASC
                    """

                    revision_history_df = pd.read_sql_query(revision_history_query, conn)

                    # Show revision history if there are previous versions
                    if len(revision_history_df) > 0:
                        st.markdown(f"**📜 Revision History** ({len(revision_history_df)} versions)")

                        with st.expander("View all revisions and feedback", expanded=False):
                            # Display each revision
                            for rev_idx, rev_row in revision_history_df.iterrows():
                                rev_num = int(rev_row['revision_number']) if pd.notna(rev_row['revision_number']) and rev_row['revision_number'] > 0 else 0

                                # Build revision label
                                if rev_num == 0:
                                    rev_label = "📄 Original Submission"
                                    status_emoji = "🟢" if rev_row['status'] == 'superseded' else "⚪"
                                else:
                                    rev_label = f"✏️ Revision {rev_num}"
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

                                # Show KB reference if available
                                if pd.notna(rev_row['kb_article_link']):
                                    st.caption(f"**KB Reference:** {rev_row['kb_article_link']}")

                                # Show issue description
                                st.markdown("**Issue Description:**")
                                st.info(rev_row['issue_description'] if pd.notna(rev_row['issue_description']) else "N/A")

                                # Show PERTS (compact view)
                                st.markdown("**PERTS / Troubleshooting:**")
                                with st.expander("View PERTS", expanded=False):
                                    st.text_area(
                                        "PERTS",
                                        value=rev_row['new_troubleshooting'] if pd.notna(rev_row['new_troubleshooting']) else "N/A",
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

                    # Get related engineer reports
                    related_reports = pd.read_sql(f"""
                        SELECT
                            report_date,
                            case_number,
                            engineer_name,
                            what_failed
                        FROM engineer_reports
                        WHERE kb_article_id = '{row['kb_article_id']}'
                        AND report_type = 'kb_outdated'
                        ORDER BY report_date DESC
                        LIMIT 5
                    """, conn)

                    if len(related_reports) > 0:
                        st.markdown("**👥 Related Engineer Reports:**")
                        st.dataframe(
                            related_reports,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "report_date": "Date",
                                "case_number": "Case #",
                                "engineer_name": "Engineer",
                                "what_failed": "What Failed"
                            }
                        )

                with col2:
                    st.markdown("**📊 Details:**")
                    if pd.notna(row.get('request_id')):
                        # Show request ID with revision number
                        if pd.notna(row.get('revision_number')) and row['revision_number'] > 0:
                            st.write(f"**Request ID:** `{row['request_id']}` (Revision {int(row['revision_number'])})")
                        else:
                            st.write(f"**Request ID:** `{row['request_id']}`")

                    # Display report type with clear labels
                    report_type = row.get('report_type', 'unknown')
                    if report_type == 'kb_missing_steps':
                        st.write(f"**Type:** 🔵 KB Missing Steps")
                        st.caption("Engineer found steps that are missing from the KB")
                    elif report_type == 'kb_outdated':
                        st.write(f"**Type:** 🟠 KB Outdated")
                        st.caption("Engineer found outdated information in the KB")
                    else:
                        st.write(f"**Type:** ⚪ {report_type}")

                    st.write(f"**Submitted by:** {row['submitted_by']}")
                    st.write(f"**Date:** {pd.to_datetime(row['submitted_date'], format='ISO8601').strftime('%Y-%m-%d')}")
                    st.write(f"**Priority:** {row['priority'].upper()}")
                    st.write(f"**Status:** {row['status'].upper()}")

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

                    # Reset to Pending button (for testing approved/rejected requests)
                    if row['status'] in ['approved', 'rejected']:
                        st.markdown("---")
                        st.markdown("**🔄 Testing Actions:**")
                        if st.button("🔄 Reset to Pending", key=f"reset_{row['id']}", use_container_width=True, type="secondary"):
                            conn_reset = get_db_connection()
                            cursor_reset = conn_reset.cursor()
                            cursor_reset.execute("""
                                UPDATE kb_update_requests
                                SET status = 'pending',
                                    reviewed_date = NULL,
                                    reviewed_by = NULL,
                                    notes = NULL
                                WHERE id = ?
                            """, (row['id'],))
                            conn_reset.commit()
                            conn_reset.close()
                            st.success(f"✅ Request {row['request_id']} reset to pending")
                            st.rerun()

                    # Action buttons (for pending and pending follow-up status)
                    if row['status'] in ['pending', 'pending follow-up']:
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
                                    # Capture values BEFORE dialog to avoid closure issues
                                    current_row_id = row['id']
                                    current_request_id = row['request_id']
                                    current_related_report_ids = row['related_report_ids']
                                    current_kb_link = row.get('kb_article_link', '')
                                    current_product = row.get('product')
                                    current_issue = row.get('issue_description')

                                    # Show approval modal
                                    @st.dialog(f"Approve Request {current_request_id}", width="large")
                                    def show_approval_modal():
                                        st.markdown("### ✅ Approve KB Update")
                                        st.caption("Provide the KB article link to notify the engineer.")

                                        with st.form(key=f"approve_form_{current_row_id}"):
                                            kb_link = st.text_input(
                                                "KB Article Link (Required)",
                                                value=current_kb_link,
                                                placeholder="https://helpcenter.trendmicro.com/en-us/article/tmka-XXXXX",
                                                key=f"approve_kb_link_{current_row_id}"
                                            )

                                            st.divider()

                                            col1, col2 = st.columns(2)
                                            with col1:
                                                cancel_btn = st.form_submit_button("Cancel", use_container_width=True)
                                            with col2:
                                                submit_btn = st.form_submit_button("✉️ Send Approval Email", use_container_width=True, type="primary")

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
                                                            WHERE id = ?
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
                                                                # Update status to approved and store KB link in proper column
                                                                cursor_approve.execute("""
                                                                    UPDATE kb_update_requests
                                                                    SET status = 'approved',
                                                                        reviewed_date = ?,
                                                                        reviewed_by = ?,
                                                                        approved_kb_link = ?
                                                                    WHERE id = ?
                                                                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), siebel_id.strip(), kb_link.strip(), current_row_id))

                                                                # Close ALL other records with the same request_id (past and future revisions)
                                                                cursor_approve.execute("""
                                                                    UPDATE kb_update_requests
                                                                    SET status = 'closed'
                                                                    WHERE request_id = ?
                                                                      AND id != ?
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
                                if siebel_id and siebel_id.strip():
                                    # Capture values BEFORE dialog to avoid closure issues
                                    current_row_id = row['id']
                                    current_request_id = row['request_id']
                                    current_related_report_ids = row['related_report_ids']
                                    current_kb_link = row.get('kb_article_link')
                                    current_product = row.get('product')
                                    current_issue = row.get('issue_description')

                                    # Show rejection modal
                                    @st.dialog(f"Request Follow-up for {current_request_id}", width="large")
                                    def show_rejection_modal():
                                        st.markdown("### 📝 Provide Structured Feedback")
                                        st.caption("Help the engineer improve their submission by providing specific feedback. They'll be able to revise and resubmit.")

                                        # Check for saved draft
                                        draft_key = f"feedback_draft_{current_row_id}"
                                        if draft_key in st.session_state:
                                            st.info("💾 Draft feedback restored from last session")
                                            draft_data = st.session_state[draft_key]
                                            default_general = draft_data.get('general', '')
                                            default_technical = draft_data.get('technical', '')
                                            default_missing = draft_data.get('missing', '')
                                            default_suggestions = draft_data.get('suggestions', '')
                                        else:
                                            default_general = ''
                                            default_technical = ''
                                            default_missing = ''
                                            default_suggestions = ''

                                        with st.form(key=f"reject_form_{current_row_id}"):
                                            # General Feedback
                                            st.markdown("**General Feedback** (Required)")
                                            general_feedback = st.text_area(
                                                "Overall assessment and main concerns",
                                                value=default_general,
                                                height=100,
                                                placeholder="Example: The troubleshooting steps are incomplete and need more detail...",
                                                key=f"general_feedback_{current_row_id}",
                                                label_visibility="collapsed"
                                            )

                                            # Technical Issues
                                            st.markdown("**Technical Issues**")
                                            technical_issues = st.text_area(
                                                "Technical problems or inaccuracies",
                                                height=80,
                                                placeholder="Example: The root cause analysis is missing key diagnostic steps...",
                                                key=f"technical_issues_{current_row_id}",
                                                label_visibility="collapsed"
                                            )

                                            # Missing Information
                                            st.markdown("**Missing Information**")
                                            missing_info = st.text_area(
                                                "Required information that is missing",
                                                height=80,
                                                placeholder="Example: Please include error messages, logs, or screenshots...",
                                                key=f"missing_info_{current_row_id}",
                                                label_visibility="collapsed"
                                            )

                                            # Improvement Suggestions
                                            st.markdown("**Suggestions for Improvement**")
                                            suggestions = st.text_area(
                                                "Specific recommendations",
                                                height=80,
                                                placeholder="Example: Consider adding a step about checking system requirements...",
                                                key=f"suggestions_{current_row_id}",
                                                label_visibility="collapsed"
                                            )

                                            st.divider()

                                            col1, col2 = st.columns(2)
                                            with col1:
                                                cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

                                            with col2:
                                                submit_btn = st.form_submit_button("✉️ Send Follow-up Email", use_container_width=True, type="primary")

                                        if submit_btn:
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
                                            if not general_feedback or not general_feedback.strip():
                                                st.error("⚠️ Please provide at least general feedback")
                                            else:
                                                # Get engineer email
                                                conn_reject = get_db_connection()
                                                cursor_reject = conn_reject.cursor()

                                                # Get engineer email from related report
                                                if current_related_report_ids:
                                                    report_id = str(current_related_report_ids).split(',')[0]
                                                    print(f"DEBUG: Looking up report_id: {report_id}")  # DEBUG
                                                    cursor_reject.execute("""
                                                        SELECT engineer_email, engineer_name
                                                        FROM engineer_reports
                                                        WHERE id = ?
                                                    """, (report_id,))
                                                    engineer_data = cursor_reject.fetchone()
                                                    print(f"DEBUG: Engineer data: {engineer_data}")  # DEBUG

                                                    if engineer_data:
                                                        engineer_email = engineer_data[0]
                                                        engineer_name = engineer_data[1]
                                                        print(f"DEBUG: Email: {engineer_email}, Name: {engineer_name}")  # DEBUG

                                                        # Check if email exists
                                                        if not engineer_email:
                                                            st.error(f"❌ This request has no email address (Report ID: {report_id}). Please ask the engineer to resubmit with their email.")
                                                            conn_reject.close()
                                                            return

                                                        # Generate revision token and link
                                                        import sys
                                                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                                                        from utils.token_generator_simple import generate_token
                                                        from utils.email_sender import send_rejection_email

                                                        revision_token = generate_token(current_request_id, 'revision')
                                                        # Link to standalone revision portal (runs on port 8502)
                                                        revision_link = f"http://localhost:8502?token={revision_token}"

                                                        # Send follow-up email
                                                        with st.spinner("📧 Sending follow-up email..."):
                                                            email_result = send_rejection_email(
                                                                request_id=current_request_id,
                                                                engineer_email=engineer_email,
                                                                engineer_name=engineer_name,
                                                                feedback_text=feedback.strip(),
                                                                kb_link=current_kb_link,
                                                                product=current_product,
                                                                issue_title=current_issue,
                                                                revision_link=revision_link
                                                            )

                                                        if email_result['success']:
                                                            # Update status to pending follow-up (not rejected)
                                                            cursor_reject.execute("""
                                                                UPDATE kb_update_requests
                                                                SET status = 'pending follow-up',
                                                                    reviewed_date = ?,
                                                                    reviewed_by = ?,
                                                                    notes = ?
                                                                WHERE id = ?
                                                            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), siebel_id.strip(), feedback.strip(), current_row_id))
                                                            conn_reject.commit()
                                                            conn_reject.close()

                                                            # Show success message
                                                            st.success(f"✅ Email sent successfully to {engineer_email}")
                                                            st.info(f"📧 The engineer has been notified with structured feedback")
                                                            st.info(f"📋 Status updated to: **Pending Follow-up**")
                                                            st.balloons()

                                                            # Wait before reloading
                                                            import time
                                                            time.sleep(2)
                                                            st.rerun()
                                                        else:
                                                            st.error(f"❌ Failed to send email: {email_result['message']}")
                                                            conn_reject.close()
                                                    else:
                                                        st.error("❌ Engineer email not found in related report")
                                                        conn_reject.close()
                                                else:
                                                    st.error("❌ No related report found for this request")

                                    show_rejection_modal()
                                else:
                                    st.error("⚠️ Please enter your Siebel ID")

                        with col_c:
                            if st.button("🤖 Generate New Step", key=f"ai_draft_{row['id']}", use_container_width=True):
                                # Import AI generator
                                import sys
                                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                                from ai_kb_generator import generate_incremental_kb_update

                                with st.spinner("🤖 Generating new troubleshooting step..."):
                                    try:
                                        # Determine update type
                                        update_type = row.get('report_type', 'kb_outdated')

                                        # Get manager notes/feedback and engineer notes (for context)
                                        manager_notes = row.get('notes') if pd.notna(row.get('notes')) else None
                                        engineer_notes = row.get('engineer_notes') if pd.notna(row.get('engineer_notes')) else None

                                        # Generate ONLY the new step (not the complete KB yet)
                                        result = generate_incremental_kb_update(
                                            current_kb_content=kb['content'],
                                            current_kb_title=kb['title'],
                                            issue_description=row['issue_description'],
                                            new_troubleshooting=row['new_troubleshooting'],
                                            update_type=update_type,
                                            product=row['product'],
                                            manager_notes=manager_notes,
                                            engineer_notes=engineer_notes
                                        )

                                        if result and result.get('content'):
                                            # Save ONLY the new step as draft
                                            new_step_content = result.get('content', '')

                                            cursor = conn.cursor()
                                            cursor.execute("""
                                                INSERT INTO kb_drafts (
                                                    report_id, title, content, created_at, status
                                                ) VALUES (?, ?, ?, ?, 'draft')
                                            """, (
                                                row['id'],
                                                f"New Step for KB-{kb['kb_number']}",
                                                new_step_content,
                                                datetime.now().isoformat()
                                            ))
                                            draft_id = cursor.lastrowid
                                            conn.commit()

                                            # Show modal dialog with JUST the new step
                                            @st.dialog(f"🤖 AI-Generated New Step (Draft ID: {draft_id})", width="large")
                                            def show_draft():
                                                st.markdown(f"### 📝 New Troubleshooting Step")
                                                st.caption(f"For KB-{kb['kb_number']} - {kb['title']}")
                                                st.divider()

                                                # Editable new step content
                                                edited_step = st.text_area(
                                                    "New Step Content (you can edit this)",
                                                    value=new_step_content,
                                                    height=300,
                                                    key=f"edit_step_{draft_id}"
                                                )

                                                st.divider()

                                                # Preview the new step
                                                with st.expander("📄 Preview New Step", expanded=True):
                                                    st.markdown(edited_step)

                                                st.divider()

                                                # Button to apply to actual KB
                                                st.markdown("### 📝 Apply to KB Article")
                                                st.caption("Click below to insert this step into the actual KB article")

                                                if st.button("📝 Apply to KB and Show Complete Article", key=f"apply_kb_{draft_id}", use_container_width=True):
                                                    # Apply the step to the KB
                                                    from ai_kb_generator import apply_incremental_update_to_kb

                                                    updated_kb_html = apply_incremental_update_to_kb(
                                                        current_kb_content=kb['content'],
                                                        new_step_content=edited_step,
                                                        update_type=update_type
                                                    )

                                                    # Update the draft with complete KB
                                                    conn_update = get_db_connection()
                                                    cursor = conn_update.cursor()
                                                    cursor.execute("""
                                                        UPDATE kb_drafts
                                                        SET content = ?,
                                                            title = ?
                                                        WHERE id = ?
                                                    """, (updated_kb_html, f"KB-{kb['kb_number']} - {kb['title']} (COMPLETE)", draft_id))
                                                    conn_update.commit()
                                                    conn_update.close()

                                                    st.success("✅ Step applied to KB!")
                                                    st.divider()

                                                    # Show complete updated KB with nice formatting
                                                    st.markdown("### 📄 Complete Updated KB Article")
                                                    st.caption("This is how the KB looks with your new step inserted")

                                                    # Format plain text KB content nicely
                                                    import re

                                                    def format_kb_content(content):
                                                        """Format plain text KB content with markdown - works for all KBs"""
                                                        # Strip HTML tags first if any
                                                        content = re.sub(r'<[^>]+>', '', content)

                                                        # Remove "Views:" from the beginning
                                                        content = re.sub(r'^Views:\s*', '', content, flags=re.IGNORECASE)

                                                        # Step 1: Collapse lines that are part of same sentence
                                                        lines = content.split('\n')
                                                        collapsed = []
                                                        current = ""
                                                        skip_until_blank = False

                                                        for i, line in enumerate(lines):
                                                            line = line.strip()

                                                            # Skip Keywords section entirely
                                                            if line.lower().startswith('keywords:'):
                                                                skip_until_blank = True
                                                                continue

                                                            if skip_until_blank:
                                                                if not line:
                                                                    skip_until_blank = False
                                                                continue

                                                            if not line:
                                                                if current:
                                                                    collapsed.append(current)
                                                                    current = ""
                                                                collapsed.append("")  # Preserve empty lines
                                                                continue

                                                            # Check if this line is a REAL heading (very strict criteria)
                                                            # Must be substantive and contain heading-like words OR be a question
                                                            is_real_heading = False
                                                            if line[0].isupper() and not line.endswith(('.', ',')):
                                                                # Question headings
                                                                if '?' in line:
                                                                    is_real_heading = True
                                                                # Must be 4+ words AND contain heading keywords
                                                                elif (len(line.split()) >= 4 and
                                                                      any(keyword in line for keyword in [
                                                                          'Did This Happen', 'Should I Do', 'Still', 'Troubleshoot',
                                                                          'Fix', 'Resolve', 'Issue', 'Error', 'Problem', 'Steps',
                                                                          'Solution', 'Method', 'Remove', 'Install', 'Configure'
                                                                      ])):
                                                                    is_real_heading = True

                                                            # If we have accumulated text and this is a heading, flush it
                                                            if is_real_heading and current:
                                                                collapsed.append(current.strip())
                                                                current = ""

                                                            # If line ends with sentence-ending punctuation, it's complete
                                                            if line.endswith(('.', '!', '?', ':')):
                                                                current = current + " " + line if current else line
                                                                collapsed.append(current.strip())
                                                                current = ""
                                                            # This is a real heading - add it immediately
                                                            elif is_real_heading:
                                                                collapsed.append(line)
                                                            # Otherwise, accumulate the line (including fragments)
                                                            else:
                                                                current = current + " " + line if current else line

                                                        if current:
                                                            collapsed.append(current.strip())

                                                        # Step 2: Format the collapsed lines
                                                        formatted = []
                                                        step_counter = 0

                                                        for i, line in enumerate(collapsed):
                                                            if not line:
                                                                formatted.append("")
                                                                step_counter = 0  # Reset numbering on blank lines
                                                                continue

                                                            # Detect headings with question marks
                                                            if '?' in line and len(line) < 100:
                                                                formatted.append(f'\n## {line}\n')
                                                                step_counter = 0
                                                            # Detect headings: title case, no period at end, moderate length
                                                            # Match things like "It Still Opens New Tabs", "Remove the TM Toolbar to Resolve Page Issues"
                                                            elif (line and line[0].isupper() and
                                                                  not line.endswith(('.', ',')) and
                                                                  not line.endswith(':') and
                                                                  len(line.split()) >= 2 and
                                                                  len(line.split()) <= 20 and
                                                                  not re.match(r'^\d+\.', line)):  # Not already numbered
                                                                # Check if it's NOT a regular sentence (doesn't start with The, A, An, If, When, After)
                                                                if not line.startswith(('The ', 'A ', 'An ', 'If ', 'When ', 'After ', 'This ', 'That ')):
                                                                    formatted.append(f'\n### {line}\n')
                                                                    step_counter = 0
                                                                else:
                                                                    # It's a regular sentence
                                                                    formatted.append(line)
                                                            # Detect action steps - start with action verb and end with period
                                                            elif line.endswith('.') and len(line.split()) > 2:
                                                                # Check if it's an action step
                                                                is_action_step = (
                                                                    line.startswith(('Click', 'Open', 'Right-click', 'Select', 'Download',
                                                                                    'Double-click', 'Log onto', 'Log in', 'Restart', 'Check',
                                                                                    'Navigate', 'Follow', 'Locate', 'Remove', 'Close',
                                                                                    'Try', 'Go to', 'Go back', 'Look for', 'If you', 'To ',
                                                                                    'Ensure', 'Verify', 'Press', 'Type', 'Enter', 'The ')) or
                                                                    re.match(r'^\d+\.', line)
                                                                )

                                                                if is_action_step:
                                                                    # Remove existing numbers if present
                                                                    clean_line = re.sub(r'^\d+\.\s*', '', line)
                                                                    step_counter += 1
                                                                    formatted.append(f'{step_counter}. {clean_line}')
                                                                else:
                                                                    # Regular paragraph text that ends with period
                                                                    formatted.append(line)
                                                            # Regular paragraph text
                                                            else:
                                                                formatted.append(line)
                                                                # Don't reset counter if it's description text after heading

                                                        # Join and clean up excessive whitespace
                                                        text = '\n'.join(formatted)
                                                        text = re.sub(r'\n\n\n+', '\n\n', text)
                                                        return text.strip()

                                                    # Format the content
                                                    formatted_content = format_kb_content(updated_kb_html)

                                                    # Display with expander like Preview
                                                    with st.expander("📄 Preview Complete Updated KB", expanded=True):
                                                        st.markdown(formatted_content)

                                            show_draft()
                                        else:
                                            st.error(f"❌ Failed to generate updated KB")
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                                        import traceback
                                        st.code(traceback.format_exc())

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
                                        placeholder="Example: Not applicable to this product / Duplicate of REQ-000123 / Out of scope for KB updates",
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
                                            # Create NEW database connection (conn might be closed)
                                            conn_close = get_db_connection()
                                            cursor_close = conn_close.cursor()
                                            cursor_close.execute("""
                                                UPDATE kb_update_requests
                                                SET status = 'rejected',
                                                    reviewed_date = ?,
                                                    reviewed_by = ?,
                                                    notes = ?
                                                WHERE id = ?
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
                                    UPDATE kb_update_requests
                                    SET notes = ?
                                    WHERE id = ?
                                """, (notes, row['id']))
                                conn.commit()
                                st.success("Notes saved!")
                                st.rerun()


                    elif row['status'] == 'approved':
                        st.markdown("---")
                        st.markdown("**📋 Close Request:**")
                        st.caption("Engineer has verified the KB article. Close this request to move it to history.")

                        if st.button("✅ Close Request", key=f"close_{row['id']}", use_container_width=True, type="primary"):
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE kb_update_requests
                                SET status = 'closed'
                                WHERE id = ?
                            """, (row['id'],))
                            conn.commit()
                            st.success("✅ Request closed successfully!")
                            st.info("📂 Request moved to closed history with status: Approved")
                            import time
                            time.sleep(2)
                            st.rerun()

                st.divider()

    else:
        st.info(f"No {status_filter} KB update requests found for the selected filters")

    conn.close()

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.code(str(e))
