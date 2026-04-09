"""
KB Assist - Home Dashboard
Support Engineer Field Reporting System
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import threading
import sys

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'database'))
from azure_db import get_connection

# Start API server in background thread (only once)
if 'api_server_started' not in st.session_state:
    try:
        # Add dashboard directory to path
        dashboard_dir = os.path.dirname(os.path.abspath(__file__))
        if dashboard_dir not in sys.path:
            sys.path.insert(0, dashboard_dir)

        from api_server import run_api_server

        # Start API server in daemon thread
        api_thread = threading.Thread(target=run_api_server, daemon=True)
        api_thread.start()
        st.session_state.api_server_started = True
        print("✅ API Server started on http://localhost:5000")
    except Exception as e:
        print(f"⚠️ Could not start API server: {e}")
        st.session_state.api_server_started = False

# Page config
st.set_page_config(
    page_title="KB Assist - Home",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #d71921;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #d71921;
    }
</style>
""", unsafe_allow_html=True)

# Database connection (Azure SQL)
def get_db_connection():
    """Get Azure SQL database connection"""
    return get_connection()

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x60/d71921/ffffff?text=KB+Assist", use_container_width=True)
    st.title("📋 KB Assist")
    st.caption("Engineer Field Reporting System")

    st.divider()

    # Product filter
    st.subheader("Filter by Product")
    products = [
        'All Products',
        'Trend Micro Scam Check',
        'Maximum Security',
        'ID Protection',
        'Mobile Security',
        'Trend Micro VPN',
        'Cleaner One Pro'
    ]

    selected_product = st.selectbox("Select Product", products, key="product_filter")

    st.divider()

    # Quick Stats
    st.subheader("Quick Stats")

    try:
        conn = get_db_connection()

        # Total reports
        query = "SELECT COUNT(*) as count FROM engineer_reports"
        if selected_product != 'All Products':
            query += f" WHERE product = '{selected_product}'"

        total = pd.read_sql(query, conn).iloc[0]['count']
        st.metric("Total Reports", f"{total:,}")

        # Pending items
        pending_updates = pd.read_sql(
            "SELECT COUNT(*) as count FROM kb_update_requests WHERE status = 'pending'",
            conn
        ).iloc[0]['count']
        st.metric("Pending Updates", pending_updates, delta=pending_updates if pending_updates > 0 else None)

        pending_new = pd.read_sql(
            "SELECT COUNT(*) as count FROM new_kb_requests WHERE status = 'pending'",
            conn
        ).iloc[0]['count']
        st.metric("Pending New KBs", pending_new, delta=pending_new if pending_new > 0 else None)

        conn.close()

    except Exception as e:
        st.error("Database not initialized")
        st.caption(str(e))

    st.divider()
    st.caption("v1.0.0 - Trend Micro")

# Main content
st.markdown('<p class="main-header">📊 KB Assist Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Real-time tracking of KB performance from support engineers</p>', unsafe_allow_html=True)

# Check Azure SQL database connection
try:
    test_conn = get_db_connection()
    test_conn.close()
except Exception as e:
    st.error("❌ Database connection failed!")
    st.error(f"Error: {str(e)}")
    st.info("""
    **Azure SQL Configuration Required:**

    Make sure these environment variables are set in Azure Portal:
    - AZURE_SQL_SERVER
    - AZURE_SQL_DATABASE
    - AZURE_SQL_USERNAME
    - AZURE_SQL_PASSWORD
    """)
    st.stop()

# Load data
try:
    conn = get_db_connection()

    # Overview metrics
    st.subheader("📈 Overview")

    col1, col2, col3, col4 = st.columns(4)

    # Query with product filter
    product_filter = f"WHERE product = '{selected_product}'" if selected_product != 'All Products' else ""

    with col1:
        total_reports = pd.read_sql(
            f"SELECT COUNT(*) as count FROM engineer_reports {product_filter}",
            conn
        ).iloc[0]['count']
        st.metric("Total Engineer Reports", f"{total_reports:,}")

    with col2:
        kb_worked = pd.read_sql(
            f"SELECT COUNT(*) as count FROM engineer_reports {product_filter} {'AND' if product_filter else 'WHERE'} report_type = 'kb_worked'",
            conn
        ).iloc[0]['count']
        success_rate = (kb_worked / total_reports * 100) if total_reports > 0 else 0
        st.metric("KB Success Rate", f"{success_rate:.1f}%")

    with col3:
        outdated = pd.read_sql(
            f"SELECT COUNT(*) as count FROM kb_update_requests WHERE status = 'pending'",
            conn
        ).iloc[0]['count']
        st.metric("Pending KB Updates", outdated, delta=outdated if outdated > 0 else None, delta_color="inverse")

    with col4:
        new_kb = pd.read_sql(
            f"SELECT COUNT(*) as count FROM new_kb_requests WHERE status = 'pending'",
            conn
        ).iloc[0]['count']
        st.metric("Pending New KBs", new_kb, delta=new_kb if new_kb > 0 else None, delta_color="inverse")

    st.divider()

    # Recent activity
    st.subheader("📋 Recent Engineer Reports")

    # Build product filter for subquery and main query
    subquery_filter = product_filter
    main_filter = product_filter.replace('WHERE product', 'WHERE er.product') if product_filter else ''

    recent_query = f"""
        SELECT
            er.created_at,
            er.request_id,
            er.case_number,
            er.kb_article_link,
            er.product,
            er.report_type,
            er.engineer_name,
            COALESCE(er.status, 'pending') as status
        FROM engineer_reports er
        INNER JOIN (
            SELECT request_id, MAX(created_at) as max_created_at
            FROM engineer_reports
            {subquery_filter}
            GROUP BY request_id
        ) latest ON er.request_id = latest.request_id AND er.created_at = latest.max_created_at
        {main_filter}
        ORDER BY er.created_at DESC
        LIMIT 15
    """

    recent_df = pd.read_sql(recent_query, conn)

    if len(recent_df) > 0:
        # Convert to PH timezone (UTC+8)
        recent_df['created_at'] = pd.to_datetime(recent_df['created_at'], format='ISO8601', utc=True)
        recent_df['created_at'] = recent_df['created_at'].dt.tz_convert('Asia/Manila')
        recent_df['submitted_date'] = recent_df['created_at'].dt.strftime('%Y-%m-%d %H:%M')

        # Format report type
        type_mapping = {
            'kb_worked': '✅ Worked',
            'kb_failed': '❌ Failed',
            'kb_update_request': '🔄 Update Request',
            'no_kb_exists': '➕ No KB'
        }
        recent_df['report_type'] = recent_df['report_type'].map(type_mapping)

        # Select and order columns to display
        display_df = recent_df[['submitted_date', 'request_id', 'case_number', 'product', 'report_type', 'engineer_name', 'status', 'kb_article_link']]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "submitted_date": "Date (PH Time)",
                "request_id": "Request ID",
                "case_number": "Case #",
                "product": "Product",
                "report_type": "Type",
                "engineer_name": "Engineer",
                "status": "Status",
                "kb_article_link": st.column_config.LinkColumn("KB Article", display_text="View KB")
            }
        )
    else:
        st.info("No reports yet. Engineers can start submitting reports!")

    st.divider()

    # Action cards
    st.subheader("🎯 Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 Most Updated KBs")
        st.write("View KBs receiving the most engineer reports")
        if st.button("View Dashboard →", key="view_most_updated", use_container_width=True):
            st.switch_page("pages/1_📊_Most_Updated_KBs.py")

    with col2:
        st.markdown("### ⏳ Pending KB Updates")
        st.write(f"{outdated} outdated KBs waiting for review")
        if st.button("Review Updates →", key="view_updates", use_container_width=True):
            st.switch_page("pages/2_⏳_Pending_KB_Updates.py")

    with col3:
        st.markdown("### ➕ Pending New TS")
        st.write(f"{new_kb} new troubleshooting steps to review")
        if st.button("Review New TS →", key="view_new_ts", use_container_width=True):
            st.switch_page("pages/3_➕_Pending_New_TS.py")

    # Product breakdown
    st.divider()
    st.subheader("📦 Reports by Product")

    product_stats = pd.read_sql("""
        SELECT
            product,
            COUNT(*) as total_reports,
            SUM(CASE WHEN report_type = 'kb_worked' THEN 1 ELSE 0 END) as worked,
            SUM(CASE WHEN report_type = 'kb_failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN report_type = 'kb_update_request' THEN 1 ELSE 0 END) as update_request,
            SUM(CASE WHEN report_type = 'no_kb_exists' THEN 1 ELSE 0 END) as no_kb
        FROM engineer_reports
        GROUP BY product
        ORDER BY total_reports DESC
    """, conn)

    if len(product_stats) > 0:
        product_stats['success_rate'] = (product_stats['worked'] / product_stats['total_reports'] * 100).round(1)

        st.dataframe(
            product_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "product": "Product",
                "total_reports": "Total Reports",
                "worked": "✅ Worked",
                "failed": "❌ Failed",
                "update_request": "🔄 Update Request",
                "no_kb": "➕ No KB",
                "success_rate": st.column_config.NumberColumn("Success Rate", format="%.1f%%")
            }
        )

    conn.close()

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.code(str(e))
