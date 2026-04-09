"""
Analytics Dashboard - Overview of all KB Assist metrics
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.ui_components import status_badge, metric_card, time_ago, format_timestamp

# Add database directory to path for Azure SQL connection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database'))
from azure_db import get_connection

st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")

# Page title
st.title("📊 KB Assist Analytics Dashboard")
st.caption("Real-time insights into KB submissions, engineer performance, and product health")

# Date range selector
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    date_range = st.selectbox(
        "Time Period",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
        index=1
    )

# Calculate date filter
now = datetime.now()
if date_range == "Last 7 Days":
    start_date = now - timedelta(days=7)
elif date_range == "Last 30 Days":
    start_date = now - timedelta(days=30)
elif date_range == "Last 90 Days":
    start_date = now - timedelta(days=90)
else:
    start_date = datetime(2020, 1, 1)

date_filter = start_date.strftime('%Y-%m-%d')

# Connect to Azure SQL database
conn = get_connection()

# ============================================================================
# KEY METRICS (Top Cards)
# ============================================================================

st.divider()
st.subheader("📈 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

# Total Submissions
total_submissions = pd.read_sql_query(f"""
    SELECT COUNT(*) as count FROM engineer_reports
    WHERE DATE(created_at) >= '{date_filter}'
""", conn).iloc[0]['count']

# Pending
pending_count = pd.read_sql_query(f"""
    SELECT COUNT(*) as count FROM engineer_reports
    WHERE status = 'pending' AND DATE(created_at) >= '{date_filter}'
""", conn).iloc[0]['count']

# Approved
approved_count = pd.read_sql_query(f"""
    SELECT COUNT(*) as count FROM engineer_reports
    WHERE status = 'approved' AND DATE(created_at) >= '{date_filter}'
""", conn).iloc[0]['count']

# Approval Rate
approval_rate = (approved_count / total_submissions * 100) if total_submissions > 0 else 0

# Avg Response Time (days)
avg_response_df = pd.read_sql_query(f"""
    SELECT AVG(JULIANDAY(reviewed_date) - JULIANDAY(created_at)) as avg_days
    FROM engineer_reports
    WHERE reviewed_date IS NOT NULL AND DATE(created_at) >= '{date_filter}'
""", conn)
avg_response_time = avg_response_df.iloc[0]['avg_days'] or 0

with col1:
    st.metric("Total Submissions", f"{total_submissions:,}")

with col2:
    st.metric("Pending", f"{pending_count:,}", delta=None, delta_color="off")

with col3:
    st.metric("Approved", f"{approved_count:,}", delta=f"+{approved_count}", delta_color="normal")

with col4:
    st.metric("Approval Rate", f"{approval_rate:.1f}%", delta=None)

with col5:
    st.metric("Avg Response Time", f"{avg_response_time:.1f} days", delta=None)

# ============================================================================
# ENGINEER PERFORMANCE
# ============================================================================

st.divider()
st.subheader("👥 Engineer Performance")

# Top Contributors
top_engineers = pd.read_sql_query(f"""
    SELECT
        engineer_name,
        COUNT(*) as total_submissions,
        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
        ROUND(SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as approval_rate
    FROM engineer_reports
    WHERE DATE(created_at) >= '{date_filter}'
    GROUP BY engineer_name
    ORDER BY total_submissions DESC
    LIMIT 10
""", conn)

if not top_engineers.empty:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.caption("Top 10 Contributors")
        # Display as bar chart
        import plotly.express as px
        fig = px.bar(
            top_engineers,
            x='engineer_name',
            y='total_submissions',
            color='approval_rate',
            color_continuous_scale='RdYlGn',
            labels={'engineer_name': 'Engineer', 'total_submissions': 'Submissions', 'approval_rate': 'Approval %'},
            title='Submissions by Engineer'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.caption("Leaderboard")
        for idx, row in top_engineers.head(5).iterrows():
            st.markdown(f"""
            **#{idx+1} {row['engineer_name']}**
            {row['total_submissions']} submissions | {row['approval_rate']:.0f}% approval
            """)
            st.progress(row['approval_rate'] / 100)
else:
    st.info("No engineer data available for selected time period")

# ============================================================================
# PRODUCT HEALTH DASHBOARD
# ============================================================================

st.divider()
st.subheader("🏥 Product Health")

# Submissions by Product
product_stats = pd.read_sql_query(f"""
    SELECT
        product,
        COUNT(*) as total,
        SUM(CASE WHEN report_type = 'no_kb_exists' THEN 1 ELSE 0 END) as no_kb,
        SUM(CASE WHEN report_type = 'kb_update_request' THEN 1 ELSE 0 END) as update_request
    FROM engineer_reports
    WHERE DATE(created_at) >= '{date_filter}' AND product IS NOT NULL
    GROUP BY product
    ORDER BY total DESC
    LIMIT 15
""", conn)

if not product_stats.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.caption("Issues by Product")
        import plotly.express as px
        fig = px.pie(
            product_stats,
            values='total',
            names='product',
            title='Distribution of Issues by Product'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.caption("Issue Types Breakdown")
        product_melted = product_stats.melt(
            id_vars=['product'],
            value_vars=['no_kb', 'outdated', 'missing_steps'],
            var_name='Issue Type',
            value_name='Count'
        )
        fig = px.bar(
            product_melted,
            x='product',
            y='Count',
            color='Issue Type',
            barmode='stack',
            title='Issue Types by Product'
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No product data available")

# ============================================================================
# KB QUALITY METRICS
# ============================================================================

st.divider()
st.subheader("📚 KB Quality Metrics")

col1, col2 = st.columns(2)

with col1:
    st.caption("Most Reported KB Update Requests")
    outdated_kbs = pd.read_sql_query(f"""
        SELECT
            kb_article_link,
            COUNT(*) as report_count,
            MAX(created_at) as last_reported
        FROM engineer_reports
        WHERE report_type = 'kb_update_request'
        AND kb_article_link IS NOT NULL
        AND DATE(created_at) >= '{date_filter}'
        GROUP BY kb_article_link
        ORDER BY report_count DESC
        LIMIT 10
    """, conn)

    if not outdated_kbs.empty:
        for idx, row in outdated_kbs.iterrows():
            kb_num = row['kb_article_link'].split('tmka-')[-1] if 'tmka-' in row['kb_article_link'] else 'Unknown'
            st.markdown(f"""
            **KB {kb_num}** - {row['report_count']} reports
            Last reported: {time_ago(row['last_reported'])}
            """)
            st.markdown(f"[View KB]({row['kb_article_link']})")
            st.divider()
    else:
        st.info("No outdated KB reports in this period")

with col2:
    st.caption("Products with Most KB Gaps")
    kb_gaps = pd.read_sql_query(f"""
        SELECT
            product,
            COUNT(*) as gap_count
        FROM engineer_reports
        WHERE report_type = 'no_kb_exists'
        AND DATE(created_at) >= '{date_filter}'
        GROUP BY product
        ORDER BY gap_count DESC
        LIMIT 10
    """, conn)

    if not kb_gaps.empty:
        import plotly.express as px
        fig = px.bar(
            kb_gaps,
            x='gap_count',
            y='product',
            orientation='h',
            title='KB Coverage Gaps by Product',
            labels={'gap_count': 'Number of Missing KBs', 'product': 'Product'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No KB gap reports in this period")

# ============================================================================
# TIMELINE / TREND ANALYSIS
# ============================================================================

st.divider()
st.subheader("📈 Submission Trends")

# Daily submissions over time
timeline_data = pd.read_sql_query(f"""
    SELECT
        DATE(created_at) as date,
        COUNT(*) as submissions,
        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
    FROM engineer_reports
    WHERE DATE(created_at) >= '{date_filter}'
    GROUP BY DATE(created_at)
    ORDER BY date
""", conn)

if not timeline_data.empty:
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timeline_data['date'], y=timeline_data['submissions'],
                             mode='lines+markers', name='Total', line=dict(width=3)))
    fig.add_trace(go.Scatter(x=timeline_data['date'], y=timeline_data['approved'],
                             mode='lines', name='Approved', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=timeline_data['date'], y=timeline_data['pending'],
                             mode='lines', name='Pending', line=dict(dash='dot')))

    fig.update_layout(
        title='Submissions Over Time',
        xaxis_title='Date',
        yaxis_title='Number of Submissions',
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No timeline data available")

# ============================================================================
# RECENT ACTIVITY
# ============================================================================

st.divider()
st.subheader("🕒 Recent Activity")

recent_activity = pd.read_sql_query(f"""
    SELECT
        id,
        engineer_name,
        product,
        report_type,
        status,
        created_at,
        reviewed_date
    FROM engineer_reports
    ORDER BY created_at DESC
    LIMIT 15
""", conn)

if not recent_activity.empty:
    for idx, row in recent_activity.iterrows():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 2])

        with col1:
            st.markdown(f"**{row['engineer_name']}**")
            st.caption(row['product'] or 'N/A')

        with col2:
            st.markdown(row['report_type'].replace('_', ' ').title())

        with col3:
            st.markdown(status_badge(row['status']), unsafe_allow_html=True)

        with col4:
            st.caption(time_ago(row['created_at']))

        st.divider()
else:
    st.info("No recent activity")

conn.close()
