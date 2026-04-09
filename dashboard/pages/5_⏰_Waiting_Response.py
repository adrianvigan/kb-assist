"""
Waiting for Engineer Response Dashboard
Track all requests that are awaiting engineer revisions
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))
from azure_db import get_connection

st.set_page_config(page_title="Waiting Response", page_icon="⏰", layout="wide")

# Database connection (Azure SQL)
def get_db_connection():
    return get_connection()

# Header
st.title("⏰ Waiting for Engineer Response")
st.caption("Requests awaiting revision from engineers after feedback")

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
    request_type_filter = st.selectbox(
        "Request Type",
        ["All", "KB Updates", "New TS"]
    )

with col3:
    age_filter = st.selectbox(
        "Age",
        ["All", "< 24 hours", "1-3 days", "3-7 days", "> 7 days"]
    )

try:
    conn = get_db_connection()

    # Get requests from both kb_update_requests and new_kb_requests with status 'pending follow-up'

    # KB Update Requests
    kb_updates_query = """
        SELECT
            kbu.id,
            kbu.request_id,
            kbu.kb_article_id,
            kbu.kb_article_title as title,
            kbu.product,
            kbu.issue_description,
            kbu.submitted_by as engineer_name,
            kbu.submitted_date,
            kbu.reviewed_date,
            kbu.reviewed_by,
            kbu.notes,
            er.engineer_email,
            er.report_type,
            'KB Update' as request_type
        FROM kb_update_requests kbu
        LEFT JOIN engineer_reports er ON kbu.related_report_ids = CAST(er.id AS TEXT)
        WHERE kbu.status = 'pending follow-up'
    """

    # New KB Requests
    new_kb_query = """
        SELECT
            nkr.id,
            nkr.request_id,
            NULL as kb_article_id,
            nkr.issue_title as title,
            nkr.product,
            nkr.issue_description,
            nkr.submitted_by as engineer_name,
            nkr.submitted_date,
            nkr.reviewed_date,
            nkr.reviewed_by,
            nkr.notes,
            er.engineer_email,
            'no_kb_exists' as report_type,
            'New KB' as request_type
        FROM new_kb_requests nkr
        LEFT JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS TEXT)
        WHERE nkr.status = 'pending follow-up'
    """

    # Combine both and wrap in subquery for consistent ordering
    # Apply request type filter
    if request_type_filter == "KB Updates":
        combined_query = f"""
            SELECT * FROM (
                {kb_updates_query}
            ) as combined
        """
    elif request_type_filter == "New TS":
        combined_query = f"""
            SELECT * FROM (
                {new_kb_query}
            ) as combined
        """
    else:
        combined_query = f"""
            SELECT * FROM (
                {kb_updates_query}
                UNION ALL
                {new_kb_query}
            ) as combined
        """

    # Add product filter if needed
    if selected_product != 'All Products':
        combined_query += f" WHERE product = '{selected_product}'"

    combined_query += " ORDER BY reviewed_date DESC"

    df = pd.read_sql(combined_query, conn)

    # Calculate days waiting
    df['reviewed_date'] = pd.to_datetime(df['reviewed_date'])
    df['days_waiting'] = (datetime.now() - df['reviewed_date']).dt.days

    # Apply age filter
    if age_filter != "All":
        if age_filter == "< 24 hours":
            df = df[df['days_waiting'] < 1]
        elif age_filter == "1-3 days":
            df = df[(df['days_waiting'] >= 1) & (df['days_waiting'] <= 3)]
        elif age_filter == "3-7 days":
            df = df[(df['days_waiting'] > 3) & (df['days_waiting'] <= 7)]
        elif age_filter == "> 7 days":
            df = df[df['days_waiting'] > 7]

    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Waiting", len(df))

    with col2:
        overdue = len(df[df['days_waiting'] > 7])
        st.metric("Overdue (>7 days)", overdue, delta=f"-{overdue}" if overdue > 0 else "0", delta_color="inverse")

    with col3:
        recent = len(df[df['days_waiting'] < 1])
        st.metric("Recent (<24h)", recent)

    with col4:
        if len(df) > 0:
            avg_days = df['days_waiting'].mean()
            st.metric("Avg Days Waiting", f"{avg_days:.1f}")
        else:
            st.metric("Avg Days Waiting", "0.0")

    st.divider()

    # Display requests
    if len(df) == 0:
        st.info("✅ No requests waiting for engineer response!")
    else:
        st.subheader(f"📋 {len(df)} Request{'s' if len(df) != 1 else ''} Awaiting Response")

        for idx, row in df.iterrows():
            # Color coding based on age
            if row['days_waiting'] > 7:
                border_color = "#dc3545"  # Red for overdue
                status_emoji = "🔴"
            elif row['days_waiting'] > 3:
                border_color = "#ffc107"  # Yellow for warning
                status_emoji = "🟡"
            else:
                border_color = "#28a745"  # Green for recent
                status_emoji = "🟢"

            with st.container():
                st.markdown(f"""
                <div style="border-left: 4px solid {border_color}; padding-left: 15px; margin-bottom: 20px;">
                """, unsafe_allow_html=True)

                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"### {status_emoji} {row['request_id']} - {row['title']}")
                    st.caption(f"**Type:** {row['request_type']} | **Product:** {row['product']}")

                    if pd.notna(row['issue_description']):
                        st.markdown("**Issue:**")
                        st.info(row['issue_description'][:200] + "..." if len(str(row['issue_description'])) > 200 else row['issue_description'])

                with col2:
                    st.markdown("**📊 Details:**")
                    st.write(f"**Engineer:** {row['engineer_name']}")
                    if pd.notna(row['engineer_email']):
                        st.write(f"**Email:** {row['engineer_email']}")
                    st.write(f"**Reviewed by:** {row['reviewed_by']}")
                    st.write(f"**Feedback sent:** {row['reviewed_date'].strftime('%Y-%m-%d')}")

                    # Waiting time with color
                    days = row['days_waiting']
                    if days > 7:
                        st.error(f"⏰ **Waiting: {days} days** (OVERDUE)")
                    elif days > 3:
                        st.warning(f"⏰ **Waiting: {days} days**")
                    else:
                        st.success(f"⏰ **Waiting: {days} days**")

                # Show manager feedback
                if pd.notna(row['notes']):
                    with st.expander("📝 View Manager Feedback", expanded=False):
                        notes = row['notes']

                        # Try to extract feedback from notes
                        if 'GENERAL FEEDBACK:' in notes or 'TECHNICAL ISSUES:' in notes:
                            st.markdown(f"""
                            <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; border-radius: 5px;">
                                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; margin: 0; font-size: 12px;">{notes}</pre>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.caption(notes)

                # Action buttons
                st.markdown("---")
                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button("🔄 Reset to Pending", key=f"reset_{row['id']}_{row['request_type']}", use_container_width=True):
                        # Reset status back to pending
                        cursor = conn.cursor()
                        if row['request_type'] == 'KB Update':
                            cursor.execute("""
                                UPDATE kb_update_requests
                                SET status = 'pending'
                                WHERE id = %s
                            """, (row['id'],))
                        else:
                            cursor.execute("""
                                UPDATE new_kb_requests
                                SET status = 'pending'
                                WHERE id = %s
                            """, (row['id'],))
                        conn.commit()
                        st.success(f"✅ {row['request_id']} reset to pending")
                        st.rerun()

                with col_b:
                    if st.button("❌ Cancel Request", key=f"cancel_{row['id']}_{row['request_type']}", use_container_width=True):
                        # Capture values for modal
                        current_cancel_id = row['id']
                        current_cancel_request_id = row['request_id']
                        current_cancel_type = row['request_type']
                        current_cancel_email = row.get('engineer_email')
                        current_cancel_engineer = row.get('engineer_name')

                        # Show cancellation modal
                        @st.dialog(f"⚠️ Cancel Request {current_cancel_request_id}", width="large")
                        def show_cancel_modal():
                            st.markdown("### ❌ Cancel Request")
                            st.warning("This will permanently reject the request and notify the engineer.")

                            st.markdown("**Reason for Cancellation (Required):**")
                            cancel_reason = st.text_area(
                                "Explain why this request is being cancelled",
                                height=100,
                                placeholder="Example: Request no longer needed / Duplicate submission / Out of scope",
                                key=f"cancel_reason_{current_cancel_id}",
                                label_visibility="collapsed"
                            )

                            # Siebel ID for cancellation
                            cancel_siebel_id = st.text_input(
                                "Your Siebel ID (required)",
                                key=f"cancel_siebel_{current_cancel_id}",
                                placeholder="e.g., adriane"
                            )

                            st.divider()

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Cancel", use_container_width=True):
                                    st.rerun()
                            with col2:
                                confirm_cancel = st.button("❌ Confirm Cancellation", use_container_width=True, type="primary")

                            if confirm_cancel:
                                if not cancel_reason or not cancel_reason.strip():
                                    st.error("⚠️ Please provide a reason for cancellation")
                                elif not cancel_siebel_id or not cancel_siebel_id.strip():
                                    st.error("⚠️ Please enter your Siebel ID")
                                else:
                                    # Update request to rejected
                                    conn_cancel = get_db_connection()
                                    cursor_cancel = conn_cancel.cursor()

                                    if current_cancel_type == 'KB Update':
                                        cursor_cancel.execute("""
                                            UPDATE kb_update_requests
                                            SET status = 'rejected',
                                                reviewed_date = %s,
                                                reviewed_by = %s,
                                                notes = %s
                                            WHERE id = %s
                                        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cancel_siebel_id.strip(),
                                              f"[CANCELLED]\n{cancel_reason}", current_cancel_id))
                                    else:
                                        cursor_cancel.execute("""
                                            UPDATE new_kb_requests
                                            SET status = 'rejected',
                                                reviewed_date = %s,
                                                reviewed_by = %s,
                                                notes = %s
                                            WHERE id = %s
                                        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cancel_siebel_id.strip(),
                                              f"[CANCELLED]\n{cancel_reason}", current_cancel_id))

                                    conn_cancel.commit()
                                    conn_cancel.close()

                                    st.success(f"✅ Request {current_cancel_request_id} cancelled by {cancel_siebel_id}")

                                    # Send cancellation email
                                    if current_cancel_email:
                                        import sys
                                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                                        from utils.email_sender import send_cancellation_email

                                        with st.spinner("📧 Sending cancellation email..."):
                                            email_result = send_cancellation_email(
                                                request_id=current_cancel_request_id,
                                                engineer_email=current_cancel_email,
                                                engineer_name=current_cancel_engineer or "Engineer",
                                                reason=cancel_reason,
                                                reviewed_by=cancel_siebel_id.strip()
                                            )

                                            if email_result['success']:
                                                st.success(f"📧 Cancellation email sent to {current_cancel_email}")
                                            else:
                                                st.warning(f"⚠️ Email failed: {email_result.get('error', 'Unknown error')}")
                                    else:
                                        st.warning("⚠️ No engineer email found - notification not sent")

                                    st.balloons()
                                    import time
                                    time.sleep(2)
                                    st.rerun()

                        show_cancel_modal()

                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    import traceback
    st.code(traceback.format_exc())

finally:
    if 'conn' in locals():
        conn.close()
