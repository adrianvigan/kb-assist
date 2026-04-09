"""
Create PostgreSQL Database Schema for KB Assist
Uses Neon.tech free PostgreSQL database
"""
from azure_db import get_connection_context

def create_tables():
    """Create all database tables in PostgreSQL"""

    with get_connection_context() as conn:
        cursor = conn.cursor()

        print("Creating engineer_reports table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engineer_reports (
                id SERIAL PRIMARY KEY,
                report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                case_number VARCHAR(100),
                kb_article_id VARCHAR(50),
                kb_article_title VARCHAR(500),
                product VARCHAR(100),
                report_type VARCHAR(50),
                -- Report types: 'kb_worked', 'kb_failed', 'kb_outdated', 'no_kb_exists'

                -- For kb_failed and kb_outdated
                what_failed TEXT,
                steps_that_failed TEXT,

                -- For kb_outdated and no_kb_exists
                new_troubleshooting TEXT,
                new_ts_steps TEXT,

                -- Common fields
                engineer_name VARCHAR(200),
                engineer_email VARCHAR(200),
                customer_environment VARCHAR(500),
                resolution_time INTEGER,

                -- Status tracking
                status VARCHAR(50) DEFAULT 'pending',
                -- Status: 'pending', 'approved', 'rejected', 'kb_created'

                reviewed_by VARCHAR(200),
                reviewed_date TIMESTAMP,
                notes TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Additional fields
                case_url VARCHAR(500),
                request_id VARCHAR(20),
                kb_article_link VARCHAR(500)
            )
        ''')
        print("engineer_reports table created")

        print("Creating kb_update_requests table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kb_update_requests (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(20) UNIQUE,
                kb_article_id VARCHAR(50) NOT NULL,
                kb_article_title VARCHAR(500),
                product VARCHAR(100),
                issue_description TEXT,
                new_troubleshooting TEXT,
                submitted_by VARCHAR(200),
                submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                priority VARCHAR(20) DEFAULT 'normal',
                related_report_ids TEXT,
                reviewed_by VARCHAR(200),
                reviewed_date TIMESTAMP,
                notes TEXT,
                revision_number INTEGER DEFAULT 1,
                original_request_id VARCHAR(20)
            )
        ''')
        print("kb_update_requests table created")

        print("Creating new_kb_requests table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS new_kb_requests (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(20) UNIQUE,
                issue_title VARCHAR(500) NOT NULL,
                product VARCHAR(100),
                issue_description TEXT,
                new_troubleshooting TEXT,
                new_ts_steps TEXT,
                submitted_by VARCHAR(200),
                submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                priority VARCHAR(20) DEFAULT 'normal',
                related_report_ids TEXT,
                reviewed_by VARCHAR(200),
                reviewed_date TIMESTAMP,
                notes TEXT,
                troubleshooting_steps TEXT,
                frequency_count INTEGER DEFAULT 1
            )
        ''')
        print("new_kb_requests table created")

        print("Creating kb_statistics table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kb_statistics (
                kb_article_id VARCHAR(50) PRIMARY KEY,
                kb_article_title VARCHAR(500),
                product VARCHAR(100),
                total_reports INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                outdated_count INTEGER DEFAULT 0,
                last_reported TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("kb_statistics table created")

        print("Creating indexes...")
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_product ON engineer_reports(product)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_kb_id ON engineer_reports(kb_article_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON engineer_reports(status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_report_type ON engineer_reports(report_type)
        ''')

        print("Indexes created")

    print("\n" + "="*60)
    print("PostgreSQL schema created successfully!")
    print("="*60)

def main():
    """Main function"""
    print("\n" + "="*60)
    print("KB ASSIST - PostgreSQL Schema Creation (Neon.tech)")
    print("="*60 + "\n")

    try:
        create_tables()
        print("\nAll tables and indexes created successfully!")
        print("\nNext step: Run migrate_to_postgres.py to import data from SQLite")
    except Exception as e:
        print(f"\nError creating schema: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has correct DATABASE_URL")
        print("2. Verify Neon.tech database is active")
        print("3. Test connection with: python azure_db.py")

if __name__ == '__main__':
    main()
