"""
Approved & Rejected History Dashboard
View past approved and rejected KB requests and updates
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))
from azure_db import get_connection

st.set_page_config(page_title="History", page_icon="📜", layout="wide")

# Database connection (Azure SQL)
def get_db_connection():
    return get_connection()

# Header
st.title("📜 Request History")
st.caption("View and search approved and rejected KB requests and updates")

# Search Section
st.subheader("🔍 Search")
col1, col2 = st.columns([3, 1])

with col1:
    search_term = st.text_input(
        "Search",
        placeholder="Request ID, case number, engineer name, product, title...",
        label_visibility="collapsed"
    )

with col2:
    search_in = st.selectbox(
        "Search in",
        ["Both", "New KB Requests", "KB Updates"],
        label_visibility="collapsed"
    )

st.divider()

# Tabs for different request types
tab1, tab2 = st.tabs(["📝 New KB Requests", "🔄 KB Update Requests"])

try:
    conn = get_db_connection()

    # TAB 1: New KB Requests History
    with tab1:
        st.subheader("📝 New KB Request History")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            products_new = [
                'All Products',
                'Trend Micro Scam Check',
                'Maximum Security',
                'ID Protection',
                'Mobile Security',
                'Trend Micro VPN',
                'Cleaner One Pro'
            ]
            selected_product_new = st.selectbox("Filter by Product", products_new, key="product_new")

        with col2:
            status_new = st.selectbox(
                "Status",
                ["All", "approved", "rejected", "completed"],
                key="status_new"
            )

        with col3:
            date_range_new = st.selectbox(
                "Date Range",
                ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
                key="date_new"
            )

        # Build filters
        filters_new = []

        if status_new != "All":
            filters_new.append(f"status = '{status_new}'")
        else:
            filters_new.append("status IN ('approved', 'rejected', 'completed')")

        if selected_product_new != 'All Products':
            filters_new.append(f"product = '{selected_product_new}'")

        # Date filter
        date_filters = {
            "Last 7 Days": "date(submitted_date) >= date('now', '-7 days')",
            "Last 30 Days": "date(submitted_date) >= date('now', '-30 days')",
            "Last 90 Days": "date(submitted_date) >= date('now', '-90 days')",
            "All Time": "1=1"
        }
        filters_new.append(date_filters[date_range_new])

        # Search filter
        if search_term and (search_in in ["Both", "New KB Requests"]):
            search_filter = f"""(
                request_id LIKE '%{search_term}%' OR
                issue_title LIKE '%{search_term}%' OR
                product LIKE '%{search_term}%' OR
                submitted_by LIKE '%{search_term}%' OR
                notes LIKE '%{search_term}%'
            )"""
            filters_new.append(search_filter)

        where_clause_new = " AND ".join(filters_new)

        # Get data
        new_kb_history = pd.read_sql(f"""
            SELECT
                id,
                request_id,
                issue_title,
                product,
                submitted_by,
                submitted_date,
                status,
                priority,
                reviewed_by,
                reviewed_date,
                kb_created_id,
                notes
            FROM new_kb_requests
            WHERE {where_clause_new}
            ORDER BY reviewed_date DESC, submitted_date DESC
        """, conn)

        # Metrics
        col1, col2, col3, col4 = st.columns(4)

        total_new = len(new_kb_history)
        approved_new = len(new_kb_history[new_kb_history['status'] == 'approved'])
        rejected_new = len(new_kb_history[new_kb_history['status'] == 'rejected'])
        completed_new = len(new_kb_history[new_kb_history['status'] == 'completed'])

        col1.metric("Total", total_new)
        col2.metric("✅ Approved", approved_new)
        col3.metric("❌ Rejected", rejected_new)
        col4.metric("✔️ Completed", completed_new)

        st.divider()

        if len(new_kb_history) > 0:
            # Display each request
            for idx, row in new_kb_history.iterrows():
                status_emoji = {
                    'approved': '✅',
                    'rejected': '❌',
                    'completed': '✔️'
                }.get(row['status'], '⚪')

                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(row['priority'], '⚪')

                with st.expander(
                    f"{status_emoji} {priority_emoji} **{row['issue_title']}** ({row['product']}) - {row['status'].upper()}",
                    expanded=False
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown("**📋 Request Details:**")
                        if pd.notna(row.get('request_id')):
                            st.write(f"**Request ID:** `{row['request_id']}`")
                        st.write(f"**Title:** {row['issue_title']}")
                        st.write(f"**Product:** {row['product']}")
                        st.write(f"**Status:** {row['status'].upper()}")

                        if pd.notna(row['kb_created_id']):
                            st.success(f"**KB Created:** {row['kb_created_id']}")

                        if pd.notna(row['notes']):
                            st.markdown("**📌 Notes:**")
                            st.info(row['notes'])

                    with col2:
                        st.markdown("**⏱️ Timeline:**")
                        st.write(f"**Submitted by:** {row['submitted_by']}")
                        st.write(f"**Submitted:** {pd.to_datetime(row['submitted_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M')}")

                        if pd.notna(row['reviewed_by']):
                            st.write(f"**Reviewed by:** {row['reviewed_by']}")
                            st.write(f"**Reviewed:** {pd.to_datetime(row['reviewed_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M')}")

                        st.write(f"**Priority:** {row['priority'].upper()}")

                    st.divider()
        else:
            st.info("No history found for the selected filters")

    # TAB 2: KB Update Requests History
    with tab2:
        st.subheader("🔄 KB Update Request History")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            products_update = [
                'All Products',
                'Trend Micro Scam Check',
                'Maximum Security',
                'ID Protection',
                'Mobile Security',
                'Trend Micro VPN',
                'Cleaner One Pro'
            ]
            selected_product_update = st.selectbox("Filter by Product", products_update, key="product_update")

        with col2:
            status_update = st.selectbox(
                "Status",
                ["All", "approved", "rejected", "implemented"],
                key="status_update"
            )

        with col3:
            date_range_update = st.selectbox(
                "Date Range",
                ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
                key="date_update"
            )

        # Build filters
        filters_update = []

        if status_update != "All":
            filters_update.append(f"status = '{status_update}'")
        else:
            filters_update.append("status IN ('approved', 'rejected', 'implemented')")

        if selected_product_update != 'All Products':
            filters_update.append(f"product = '{selected_product_update}'")

        filters_update.append(date_filters[date_range_update])

        # Search filter
        if search_term and (search_in in ["Both", "KB Updates"]):
            search_filter = f"""(
                request_id LIKE '%{search_term}%' OR
                kb_article_id LIKE '%{search_term}%' OR
                kb_article_title LIKE '%{search_term}%' OR
                product LIKE '%{search_term}%' OR
                submitted_by LIKE '%{search_term}%' OR
                issue_description LIKE '%{search_term}%' OR
                notes LIKE '%{search_term}%'
            )"""
            filters_update.append(search_filter)

        where_clause_update = " AND ".join(filters_update)

        # Get data
        update_history = pd.read_sql(f"""
            SELECT
                id,
                request_id,
                kb_article_id,
                kb_article_title,
                product,
                issue_description,
                submitted_by,
                submitted_date,
                status,
                priority,
                reviewed_by,
                reviewed_date,
                notes
            FROM kb_update_requests
            WHERE {where_clause_update}
            ORDER BY reviewed_date DESC, submitted_date DESC
        """, conn)

        # Metrics
        col1, col2, col3, col4 = st.columns(4)

        total_update = len(update_history)
        approved_update = len(update_history[update_history['status'] == 'approved'])
        rejected_update = len(update_history[update_history['status'] == 'rejected'])
        implemented_update = len(update_history[update_history['status'] == 'implemented'])

        col1.metric("Total", total_update)
        col2.metric("✅ Approved", approved_update)
        col3.metric("❌ Rejected", rejected_update)
        col4.metric("✔️ Implemented", implemented_update)

        st.divider()

        if len(update_history) > 0:
            # Display each request
            for idx, row in update_history.iterrows():
                status_emoji = {
                    'approved': '✅',
                    'rejected': '❌',
                    'implemented': '✔️'
                }.get(row['status'], '⚪')

                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(row['priority'], '⚪')

                kb_display = f"KB-{row['kb_article_id']}" if pd.notna(row['kb_article_id']) else "Unknown KB"
                title_display = row['kb_article_title'] if pd.notna(row['kb_article_title']) else "No Title"

                with st.expander(
                    f"{status_emoji} {priority_emoji} **{kb_display}**: {title_display} ({row['product']}) - {row['status'].upper()}",
                    expanded=False
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown("**📋 Update Details:**")
                        if pd.notna(row.get('request_id')):
                            st.write(f"**Request ID:** `{row['request_id']}`")
                        st.write(f"**KB Article:** {kb_display}")
                        st.write(f"**Product:** {row['product']}")
                        st.write(f"**Status:** {row['status'].upper()}")

                        if pd.notna(row['issue_description']):
                            st.markdown("**🔍 Issue:**")
                            st.info(row['issue_description'])

                        if pd.notna(row['notes']):
                            st.markdown("**📌 Notes:**")
                            st.warning(row['notes'])

                    with col2:
                        st.markdown("**⏱️ Timeline:**")
                        st.write(f"**Submitted by:** {row['submitted_by']}")
                        st.write(f"**Submitted:** {pd.to_datetime(row['submitted_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M')}")

                        if pd.notna(row['reviewed_by']):
                            st.write(f"**Reviewed by:** {row['reviewed_by']}")
                            st.write(f"**Reviewed:** {pd.to_datetime(row['reviewed_date'], format='ISO8601').strftime('%Y-%m-%d %H:%M')}")

                        st.write(f"**Priority:** {row['priority'].upper()}")

                    st.divider()
        else:
            st.info("No history found for the selected filters")

    conn.close()

except Exception as e:
    st.error(f"Error loading history: {str(e)}")
    st.code(str(e))
