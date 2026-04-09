"""
Add sample data to PostgreSQL database for testing
"""
from azure_db import get_connection
from datetime import datetime, timedelta

def add_sample_data():
    """Add sample data to tables"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Adding sample engineer reports...")

    # Sample data
    sample_reports = [
        {
            'case_number': 'SR-2024-001',
            'kb_article_id': '11001',
            'kb_article_title': 'How to Install Trend Micro Maximum Security',
            'product': 'Maximum Security',
            'report_type': 'kb_worked',
            'engineer_name': 'John Doe',
            'engineer_email': 'john.doe@example.com',
            'status': 'approved',
            'kb_article_link': 'https://success.trendmicro.com/kb/11001'
        },
        {
            'case_number': 'SR-2024-002',
            'kb_article_id': '11002',
            'kb_article_title': 'Troubleshooting VPN Connection Issues',
            'product': 'Trend Micro VPN',
            'report_type': 'kb_outdated',
            'what_failed': 'Steps 3-5 no longer work with latest version',
            'new_troubleshooting': 'Updated steps for version 2.0',
            'engineer_name': 'Jane Smith',
            'engineer_email': 'jane.smith@example.com',
            'status': 'pending',
            'kb_article_link': 'https://success.trendmicro.com/kb/11002'
        },
        {
            'case_number': 'SR-2024-003',
            'kb_article_id': None,
            'kb_article_title': 'Mobile Security App Crashes on Android 14',
            'product': 'Mobile Security',
            'report_type': 'no_kb_exists',
            'new_troubleshooting': 'Clear app cache, reinstall app',
            'engineer_name': 'Bob Johnson',
            'engineer_email': 'bob.johnson@example.com',
            'status': 'pending',
            'kb_article_link': None
        },
    ]

    for report in sample_reports:
        cursor.execute('''
            INSERT INTO engineer_reports (
                report_date, case_number, kb_article_id, kb_article_title,
                product, report_type, what_failed, new_troubleshooting,
                engineer_name, engineer_email, status, kb_article_link,
                created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            datetime.now(),
            report['case_number'],
            report.get('kb_article_id'),
            report['kb_article_title'],
            report['product'],
            report['report_type'],
            report.get('what_failed'),
            report.get('new_troubleshooting'),
            report['engineer_name'],
            report['engineer_email'],
            report['status'],
            report.get('kb_article_link'),
            datetime.now()
        ))

    conn.commit()
    print(f"Added {len(sample_reports)} sample reports")

    print("Adding sample KB update requests...")

    sample_kb_updates = [
        {
            'request_id': 'KBU-000001',
            'kb_article_id': '11002',
            'kb_article_title': 'Troubleshooting VPN Connection Issues',
            'product': 'Trend Micro VPN',
            'issue_description': 'Steps outdated for version 2.0',
            'new_troubleshooting': 'Updated configuration steps',
            'submitted_by': 'Jane Smith',
            'status': 'pending',
            'revision_number': 1
        },
    ]

    for req in sample_kb_updates:
        cursor.execute('''
            INSERT INTO kb_update_requests (
                request_id, kb_article_id, kb_article_title, product,
                issue_description, new_troubleshooting, submitted_by,
                submitted_date, status, revision_number
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            req['request_id'],
            req['kb_article_id'],
            req['kb_article_title'],
            req['product'],
            req['issue_description'],
            req['new_troubleshooting'],
            req['submitted_by'],
            datetime.now(),
            req['status'],
            req['revision_number']
        ))

    conn.commit()
    print(f"Added {len(sample_kb_updates)} sample KB update requests")

    print("Adding sample new KB requests...")

    sample_new_kb = [
        {
            'request_id': 'NKB-000001',
            'issue_title': 'Mobile Security App Crashes on Android 14',
            'product': 'Mobile Security',
            'issue_description': 'App crashes when opening on Android 14',
            'new_troubleshooting': 'Clear cache and reinstall',
            'troubleshooting_steps': '1. Clear app cache\n2. Uninstall app\n3. Reinstall from Play Store',
            'submitted_by': 'Bob Johnson',
            'status': 'pending'
        },
    ]

    for req in sample_new_kb:
        cursor.execute('''
            INSERT INTO new_kb_requests (
                request_id, issue_title, product, issue_description,
                new_troubleshooting, troubleshooting_steps, submitted_by,
                submitted_date, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            req['request_id'],
            req['issue_title'],
            req['product'],
            req['issue_description'],
            req['new_troubleshooting'],
            req['troubleshooting_steps'],
            req['submitted_by'],
            datetime.now(),
            req['status']
        ))

    conn.commit()
    print(f"Added {len(sample_new_kb)} sample new KB requests")

    conn.close()
    print("\nAll sample data added successfully!")
    print("You can now test the dashboard with this data.")

if __name__ == '__main__':
    add_sample_data()
