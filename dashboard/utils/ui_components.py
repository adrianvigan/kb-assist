"""
Shared UI components for KB Assist Dashboard
"""
import streamlit as st
from datetime import datetime
import pytz

def status_badge(status):
    """
    Display a colored status badge

    Args:
        status: Status string (pending, approved, rejected, etc.)

    Returns:
        HTML string with colored badge
    """
    status_lower = status.lower() if status else 'unknown'

    # Color mapping
    colors = {
        'pending': '#FFA500',      # Orange
        'approved': '#28A745',     # Green
        'rejected': '#DC3545',     # Red
        'in_progress': '#007BFF',  # Blue
        'completed': '#28A745',    # Green
        'high': '#DC3545',         # Red (for priority)
        'medium': '#FFA500',       # Orange (for priority)
        'low': '#6C757D',          # Gray (for priority)
        'critical': '#8B0000',     # Dark Red
        'resolved': '#28A745',     # Green
        'draft': '#6C757D',        # Gray
    }

    # Icon mapping
    icons = {
        'pending': '⏳',
        'approved': '✅',
        'rejected': '❌',
        'in_progress': '🔄',
        'completed': '✅',
        'high': '🔴',
        'medium': '🟡',
        'low': '⚪',
        'critical': '🔥',
        'resolved': '✅',
        'draft': '📝',
    }

    color = colors.get(status_lower, '#6C757D')
    icon = icons.get(status_lower, '•')

    badge_html = f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 2px;
        text-transform: uppercase;
    ">
        {icon} {status}
    </span>
    """

    return badge_html


def priority_badge(priority):
    """Display a colored priority badge"""
    return status_badge(priority)


def format_timestamp(timestamp_str, timezone='Asia/Manila'):
    """
    Format timestamp to Philippine time

    Args:
        timestamp_str: ISO format timestamp string
        timezone: Target timezone (default: Asia/Manila)

    Returns:
        Formatted string with date and time
    """
    if not timestamp_str:
        return 'N/A'

    try:
        # Parse timestamp
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = timestamp_str

        # Convert to target timezone
        tz = pytz.timezone(timezone)
        dt_local = dt.astimezone(tz)

        # Format
        return dt_local.strftime('%Y-%m-%d %I:%M %p')
    except Exception as e:
        return timestamp_str


def time_ago(timestamp_str):
    """
    Calculate time elapsed since timestamp

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Human-readable time difference (e.g., "2 hours ago")
    """
    if not timestamp_str:
        return 'Unknown'

    try:
        # Parse timestamp
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = timestamp_str

        # Calculate difference
        now = datetime.now(pytz.UTC)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        diff = now - dt

        seconds = diff.total_seconds()

        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} day{"s" if days != 1 else ""} ago'
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f'{weeks} week{"s" if weeks != 1 else ""} ago'
        else:
            months = int(seconds / 2592000)
            return f'{months} month{"s" if months != 1 else ""} ago'
    except Exception as e:
        return 'Unknown'


def clickable_link(url, text=None, new_tab=True):
    """
    Create a clickable hyperlink

    Args:
        url: The URL to link to
        text: Display text (default: URL)
        new_tab: Open in new tab (default: True)

    Returns:
        HTML string with hyperlink
    """
    if not url:
        return 'N/A'

    display_text = text or url
    target = '_blank' if new_tab else '_self'

    return f'<a href="{url}" target="{target}" style="color: #007BFF; text-decoration: none;">{display_text}</a>'


def metric_card(title, value, delta=None, delta_color='normal'):
    """
    Display a metric card with optional delta

    Args:
        title: Metric title
        value: Main value to display
        delta: Change/delta value
        delta_color: Color for delta (normal, inverse, off)
    """
    st.metric(label=title, value=value, delta=delta, delta_color=delta_color)


def progress_bar(current, total, label=None):
    """
    Display a progress bar

    Args:
        current: Current value
        total: Total/max value
        label: Optional label text
    """
    if total == 0:
        percentage = 0
    else:
        percentage = min(100, int((current / total) * 100))

    color = '#28A745' if percentage >= 80 else '#FFA500' if percentage >= 50 else '#DC3545'

    html = f"""
    <div style="margin: 10px 0;">
        {f'<p style="margin-bottom: 5px; font-size: 14px;">{label}</p>' if label else ''}
        <div style="background-color: #E9ECEF; border-radius: 10px; height: 20px; overflow: hidden;">
            <div style="
                background-color: {color};
                width: {percentage}%;
                height: 100%;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 12px;
                font-weight: 600;
            ">
                {percentage}%
            </div>
        </div>
    </div>
    """

    return html
