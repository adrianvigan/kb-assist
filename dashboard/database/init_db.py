"""
Initialize KB_Assist Database
Support Engineer Field Reporting System
"""

import sqlite3
import random
from datetime import datetime, timedelta

# Trend Micro Products
PRODUCTS = [
    'Trend Micro Scam Check',
    'Maximum Security',
    'ID Protection',
    'Mobile Security',
    'Trend Micro VPN',
    'Cleaner One Pro'
]

def create_tables(conn):
    """Create database tables"""
    cursor = conn.cursor()

    # Engineer Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS engineer_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            case_number TEXT,
            kb_article_id TEXT,
            kb_article_title TEXT,
            product TEXT,
            report_type TEXT,
            -- Report types: 'kb_worked', 'kb_failed', 'kb_outdated', 'no_kb_exists'

            -- For kb_failed and kb_outdated
            what_failed TEXT,
            steps_that_failed TEXT,

            -- For kb_outdated and no_kb_exists
            new_troubleshooting TEXT,
            new_ts_steps TEXT,

            -- Common fields
            engineer_name TEXT,
            engineer_email TEXT,
            customer_environment TEXT,
            resolution_time INTEGER,

            -- Status tracking
            status TEXT DEFAULT 'pending',
            -- Status: 'pending', 'approved', 'rejected', 'kb_created'

            reviewed_by TEXT,
            reviewed_date TIMESTAMP,
            notes TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # KB Update Requests Table (for outdated KBs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kb_update_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_article_id TEXT,
            kb_article_title TEXT,
            product TEXT,
            issue_description TEXT,
            new_troubleshooting TEXT,
            submitted_by TEXT,
            submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            -- Status: 'pending', 'approved', 'rejected', 'implemented'
            priority TEXT,
            related_report_ids TEXT,
            reviewed_by TEXT,
            reviewed_date TIMESTAMP,
            notes TEXT
        )
    ''')

    # New KB Requests Table (for issues with no KB)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_kb_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_title TEXT,
            product TEXT,
            issue_description TEXT,
            troubleshooting_steps TEXT,
            submitted_by TEXT,
            submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            -- Status: 'pending', 'approved', 'in_progress', 'completed', 'rejected'
            priority TEXT,
            frequency_count INTEGER DEFAULT 1,
            related_report_ids TEXT,
            assigned_to TEXT,
            kb_created_id TEXT,
            reviewed_by TEXT,
            reviewed_date TIMESTAMP,
            notes TEXT
        )
    ''')

    # KB Statistics Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kb_statistics (
            kb_article_id TEXT PRIMARY KEY,
            kb_article_title TEXT,
            product TEXT,
            total_reports INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            outdated_count INTEGER DEFAULT 0,
            last_reported TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_product ON engineer_reports(product)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kb_id ON engineer_reports(kb_article_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON engineer_reports(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_type ON engineer_reports(report_type)')

    conn.commit()
    print("✅ Tables created successfully")

def insert_sample_data(conn):
    """Insert sample data for testing"""
    cursor = conn.cursor()

    # Sample KBs
    sample_kbs = [
        ('000123456', 'How to install Maximum Security', 'Maximum Security'),
        ('000234567', 'Troubleshoot VPN connection issues', 'Trend Micro VPN'),
        ('000345678', 'Configure Scam Check settings', 'Trend Micro Scam Check'),
        ('000456789', 'Reset ID Protection password', 'ID Protection'),
        ('000567890', 'Mobile Security installation guide', 'Mobile Security'),
        ('000678901', 'Cleaner One Pro optimization steps', 'Cleaner One Pro'),
        ('000789012', 'Update Maximum Security definitions', 'Maximum Security'),
        ('000890123', 'VPN server selection guide', 'Trend Micro VPN'),
    ]

    # Sample engineers
    engineers = [
        ('John Doe', 'john.doe@trendmicro.com'),
        ('Jane Smith', 'jane.smith@trendmicro.com'),
        ('Mike Johnson', 'mike.johnson@trendmicro.com'),
        ('Sarah Williams', 'sarah.williams@trendmicro.com'),
        ('Tom Brown', 'tom.brown@trendmicro.com'),
        ('Lisa Garcia', 'lisa.garcia@trendmicro.com'),
    ]

    report_types = ['kb_worked', 'kb_failed', 'kb_outdated', 'no_kb_exists']
    statuses = ['pending', 'approved', 'rejected']

    base_date = datetime.now() - timedelta(days=30)
    report_count = 0

    # Generate engineer reports
    for day_offset in range(30):
        num_reports = random.randint(5, 15)

        for _ in range(num_reports):
            report_type = random.choices(
                report_types,
                weights=[0.5, 0.2, 0.2, 0.1],  # More success, some issues
                k=1
            )[0]

            report_date = base_date + timedelta(
                days=day_offset,
                hours=random.randint(8, 18),
                minutes=random.randint(0, 59)
            )

            engineer_name, engineer_email = random.choice(engineers)
            case_number = f"INC{random.randint(100000, 999999)}"

            # Determine status
            if report_date < datetime.now() - timedelta(days=7):
                status = random.choice(statuses)
            else:
                status = 'pending'

            if report_type == 'no_kb_exists':
                # New issue with no KB
                product = random.choice(PRODUCTS)

                cursor.execute('''
                    INSERT INTO engineer_reports (
                        report_date, case_number, product, report_type,
                        new_troubleshooting, engineer_name, engineer_email,
                        resolution_time, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_date.strftime('%Y-%m-%d %H:%M:%S'),
                    case_number,
                    product,
                    report_type,
                    f"New troubleshooting steps for {product} issue",
                    engineer_name,
                    engineer_email,
                    random.randint(20, 120),
                    status
                ))
            else:
                # Report about existing KB
                kb_id, kb_title, product = random.choice(sample_kbs)

                what_failed = None
                new_troubleshooting = None

                if report_type == 'kb_failed':
                    what_failed = f"Step {random.randint(1, 5)} failed - error encountered"
                elif report_type == 'kb_outdated':
                    what_failed = f"KB contains outdated information for {product}"
                    new_troubleshooting = f"Updated steps that work with latest version of {product}"

                cursor.execute('''
                    INSERT INTO engineer_reports (
                        report_date, case_number, kb_article_id, kb_article_title,
                        product, report_type, what_failed, new_troubleshooting,
                        engineer_name, engineer_email, resolution_time, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_date.strftime('%Y-%m-%d %H:%M:%S'),
                    case_number,
                    kb_id,
                    kb_title,
                    product,
                    report_type,
                    what_failed,
                    new_troubleshooting,
                    engineer_name,
                    engineer_email,
                    random.randint(10, 90),
                    status
                ))

            report_count += 1

    # Generate KB Update Requests (from outdated reports)
    cursor.execute('''
        SELECT kb_article_id, kb_article_title, product, new_troubleshooting,
               engineer_name, report_date
        FROM engineer_reports
        WHERE report_type = 'kb_outdated' AND status = 'pending'
        GROUP BY kb_article_id
        LIMIT 10
    ''')

    for row in cursor.fetchall():
        cursor.execute('''
            INSERT INTO kb_update_requests (
                kb_article_id, kb_article_title, product,
                issue_description, new_troubleshooting,
                submitted_by, submitted_date, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row[0], row[1], row[2],
            f"KB needs update based on field reports",
            row[3],
            row[4],
            row[5],
            random.choice(['high', 'medium', 'low'])
        ))

    # Generate New KB Requests (from no_kb_exists reports)
    cursor.execute('''
        SELECT product, new_troubleshooting, engineer_name, report_date
        FROM engineer_reports
        WHERE report_type = 'no_kb_exists' AND status = 'pending'
        GROUP BY product, new_troubleshooting
        LIMIT 15
    ''')

    for row in cursor.fetchall():
        cursor.execute('''
            INSERT INTO new_kb_requests (
                issue_title, product, issue_description,
                troubleshooting_steps, submitted_by, submitted_date, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"New issue for {row[0]}",
            row[0],
            f"Multiple engineers reporting this {row[0]} issue",
            row[1],
            row[2],
            row[3],
            random.choice(['high', 'medium', 'low'])
        ))

    # Update KB Statistics
    for kb_id, kb_title, product in sample_kbs:
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN report_type = 'kb_worked' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN report_type = 'kb_failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN report_type = 'kb_outdated' THEN 1 ELSE 0 END) as outdated,
                MAX(report_date) as last_reported
            FROM engineer_reports
            WHERE kb_article_id = ?
        ''', (kb_id,))

        stats = cursor.fetchone()

        if stats and stats[0] > 0:
            cursor.execute('''
                INSERT INTO kb_statistics (
                    kb_article_id, kb_article_title, product,
                    total_reports, success_count, failed_count,
                    outdated_count, last_reported
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (kb_id, kb_title, product, stats[0], stats[1], stats[2], stats[3], stats[4]))

    conn.commit()
    print(f"✅ Inserted {report_count} engineer reports")
    print("✅ Created KB update requests and new KB requests")

def main():
    """Main initialization"""
    print("\n" + "="*60)
    print("KB ASSIST - Database Initialization")
    print("="*60 + "\n")

    db_path = 'kb_assist.db'
    conn = sqlite3.connect(db_path)

    print("Creating tables...")
    create_tables(conn)

    print("\nInserting sample data...")
    insert_sample_data(conn)

    conn.close()

    print("\n" + "="*60)
    print("✅ Database initialized successfully!")
    print("="*60)
    print(f"\nDatabase: {db_path}")
    print("\nProducts included:")
    for product in PRODUCTS:
        print(f"  - {product}")
    print("\nNext steps:")
    print("  cd ../dashboard")
    print("  streamlit run Home.py")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
