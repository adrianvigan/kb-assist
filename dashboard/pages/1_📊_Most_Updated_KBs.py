"""
Dashboard Analytics
Shows statistics about KB requests and engineer reports
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))
from azure_db import get_connection

st.set_page_config(page_title="Dashboard Analytics", page_icon="📊", layout="wide")

# Database connection (Azure SQL)
def get_db_connection():
    return get_connection()

# Header
st.title("📊 Dashboard Analytics")
st.caption("Overview of KB requests and engineer activity")

st.divider()

try:
    conn = get_db_connection()

    # Time range filter
    col1, col2 = st.columns([1, 3])

    with col1:
        time_range = st.selectbox(
            "Time Range",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"]
        )

    # Calculate date filter (PostgreSQL syntax)
    date_filters = {
        "Last 7 Days": "created_at >= CURRENT_DATE - INTERVAL '7 days'",
        "Last 30 Days": "created_at >= CURRENT_DATE - INTERVAL '30 days'",
        "Last 90 Days": "created_at >= CURRENT_DATE - INTERVAL '90 days'",
        "All Time": "1=1"
    }
    date_filter = date_filters[time_range]

    # === KEY METRICS ===
    st.subheader("📈 Overview")

    col1, col2, col3, col4 = st.columns(4)

    # Total reports
    total_reports = pd.read_sql(f"""
        SELECT COUNT(*) as count
        FROM engineer_reports
        WHERE {date_filter}
    """, conn).iloc[0]['count']

    # New KB requests
    new_kb_count = pd.read_sql(f"""
        SELECT COUNT(*) as count
        FROM engineer_reports
        WHERE report_type = 'no_kb_exists'
        AND {date_filter}
    """, conn).iloc[0]['count']

    # KB updates needed
    kb_updates_count = pd.read_sql(f"""
        SELECT COUNT(*) as count
        FROM engineer_reports
        WHERE report_type = 'kb_update_request'
        AND {date_filter}
    """, conn).iloc[0]['count']

    # Unique engineers
    unique_engineers = pd.read_sql(f"""
        SELECT COUNT(DISTINCT engineer_name) as count
        FROM engineer_reports
        WHERE {date_filter}
    """, conn).iloc[0]['count']

    col1.metric("Total Reports", total_reports)
    col2.metric("New KB Requests", new_kb_count)
    col3.metric("KB Updates Needed", kb_updates_count)
    col4.metric("Active Engineers", unique_engineers)

    st.divider()

    # === PRODUCTS WITH MOST REPORTS ===
    st.subheader("📦 Products with Most Reports")

    product_stats = pd.read_sql(f"""
        SELECT
            product,
            COUNT(*) as total_reports,
            SUM(CASE WHEN report_type = 'no_kb_exists' THEN 1 ELSE 0 END) as new_kb_needed,
            SUM(CASE WHEN report_type = 'kb_update_request' THEN 1 ELSE 0 END) as updates_needed
        FROM engineer_reports
        WHERE {date_filter}
        GROUP BY product
        ORDER BY total_reports DESC
    """, conn)

    if len(product_stats) > 0:
        st.dataframe(
            product_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "product": "Product",
                "total_reports": st.column_config.NumberColumn("Total Reports", format="%d"),
                "new_kb_needed": st.column_config.NumberColumn("New KBs Needed", format="%d"),
                "updates_needed": st.column_config.NumberColumn("Updates Needed", format="%d")
            }
        )
    else:
        st.info("No data available for the selected time range")

    st.divider()

    # === TIMELINE VIEW - KB REQUEST FREQUENCY ===
    st.subheader("📅 KB Request Timeline (Last 30 Days)")

    timeline_data = pd.read_sql("""
        SELECT
            DATE(created_at) as date,
            COUNT(*) as total_requests,
            SUM(CASE WHEN report_type = 'no_kb_exists' THEN 1 ELSE 0 END) as new_kb_requests,
            SUM(CASE WHEN report_type = 'kb_update_request' THEN 1 ELSE 0 END) as update_requests
        FROM engineer_reports
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """, conn)

    if len(timeline_data) > 0:
        timeline_data['date'] = pd.to_datetime(timeline_data['date'])
        timeline_data['date_formatted'] = timeline_data['date'].dt.strftime('%Y-%m-%d')

        st.dataframe(
            timeline_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "date_formatted": "Date",
                "total_requests": st.column_config.NumberColumn("Total Requests", format="%d"),
                "new_kb_requests": st.column_config.NumberColumn("➕ New KB", format="%d"),
                "update_requests": st.column_config.NumberColumn("🔄 Updates", format="%d")
            },
            column_order=["date_formatted", "total_requests", "new_kb_requests", "update_requests"]
        )

        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_per_day = timeline_data['total_requests'].mean()
            st.metric("Avg Requests/Day", f"{avg_per_day:.1f}")
        with col2:
            busiest_day = timeline_data.loc[timeline_data['total_requests'].idxmax()]
            st.metric("Busiest Day", f"{busiest_day['date_formatted']}", f"{int(busiest_day['total_requests'])} requests")
        with col3:
            days_with_requests = len(timeline_data)
            st.metric("Active Days", f"{days_with_requests}/30")
    else:
        st.info("No requests in the last 30 days")

    st.divider()

    # === ENGINEER ACTIVITY ===
    st.subheader("👥 Top Contributing Engineers")

    engineer_stats = pd.read_sql(f"""
        SELECT
            engineer_name,
            COUNT(*) as total_reports,
            SUM(CASE WHEN report_type = 'no_kb_exists' THEN 1 ELSE 0 END) as new_kb_reports,
            SUM(CASE WHEN report_type = 'kb_update_request' THEN 1 ELSE 0 END) as update_reports,
            MAX(created_at) as last_report
        FROM engineer_reports
        WHERE {date_filter}
        GROUP BY engineer_name
        ORDER BY total_reports DESC
        LIMIT 10
    """, conn)

    if len(engineer_stats) > 0:
        engineer_stats['last_report'] = pd.to_datetime(engineer_stats['last_report'], format='ISO8601')
        engineer_stats['last_report_formatted'] = engineer_stats['last_report'].dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            engineer_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "engineer_name": "Engineer",
                "total_reports": st.column_config.NumberColumn("Total Reports", format="%d"),
                "new_kb_reports": st.column_config.NumberColumn("➕ New KB", format="%d"),
                "update_reports": st.column_config.NumberColumn("🔄 Updates", format="%d"),
                "last_report_formatted": "Last Report"
            },
            column_order=["engineer_name", "total_reports", "new_kb_reports", "update_reports", "last_report_formatted"]
        )
    else:
        st.info("No engineer activity for the selected time range")

    st.divider()

    # === REPORT TYPE BREAKDOWN ===
    st.subheader("📋 Report Type Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        report_type_stats = pd.read_sql(f"""
            SELECT
                report_type,
                COUNT(*) as count
            FROM engineer_reports
            WHERE {date_filter}
            GROUP BY report_type
            ORDER BY count DESC
        """, conn)

        if len(report_type_stats) > 0:
            # Map report types to friendly names
            type_mapping = {
                'no_kb_exists': '➕ No KB Exists',
                'kb_update_request': '🔄 Update Request',
                'kb_worked': '✅ KB Worked',
                'kb_failed': '❌ KB Failed'
            }

            report_type_stats['type_display'] = report_type_stats['report_type'].map(type_mapping)

            st.dataframe(
                report_type_stats,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "type_display": "Report Type",
                    "count": st.column_config.NumberColumn("Count", format="%d")
                },
                column_order=["type_display", "count"]
            )

    with col2:
        # Recent Activity
        st.markdown("**🕒 Recent Activity (Last 5)**")
        recent_activity = pd.read_sql(f"""
            SELECT
                created_at,
                product,
                report_type,
                engineer_name
            FROM engineer_reports
            WHERE {date_filter}
            ORDER BY created_at DESC
            LIMIT 5
        """, conn)

        if len(recent_activity) > 0:
            for idx, row in recent_activity.iterrows():
                created = pd.to_datetime(row['created_at'], format='ISO8601')
                time_str = created.strftime('%Y-%m-%d %H:%M')

                type_emoji = {
                    'no_kb_exists': '➕',
                    'kb_update_request': '🔄',
                    'kb_worked': '✅',
                    'kb_failed': '❌'
                }.get(row['report_type'], '📄')

                st.caption(f"{type_emoji} {row['product']} - {row['engineer_name']}")
                st.caption(f"   ⏱️ {time_str}")
                if idx < 4:
                    st.markdown("---")

    conn.close()

except Exception as e:
    st.error(f"Error loading analytics: {str(e)}")
    st.code(str(e))
