"""
Create Azure SQL Database Schema for KB Assist
Converts SQLite schema to Azure SQL (T-SQL) syntax
"""
from azure_db import get_connection_context

def create_tables():
    """Create all database tables in Azure SQL"""

    with get_connection_context() as conn:
        cursor = conn.cursor()

        print("Creating engineer_reports table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'engineer_reports')
            CREATE TABLE engineer_reports (
                id INT IDENTITY(1,1) PRIMARY KEY,
                report_date DATETIME2 DEFAULT GETDATE(),
                case_number NVARCHAR(100),
                kb_article_id NVARCHAR(50),
                kb_article_title NVARCHAR(500),
                product NVARCHAR(100),
                report_type NVARCHAR(50),
                -- Report types: 'kb_worked', 'kb_failed', 'kb_outdated', 'no_kb_exists'

                -- For kb_failed and kb_outdated
                what_failed NVARCHAR(MAX),
                steps_that_failed NVARCHAR(MAX),

                -- For kb_outdated and no_kb_exists
                new_troubleshooting NVARCHAR(MAX),
                new_ts_steps NVARCHAR(MAX),

                -- Common fields
                engineer_name NVARCHAR(200),
                engineer_email NVARCHAR(200),
                customer_environment NVARCHAR(500),
                resolution_time INT,

                -- Status tracking
                status NVARCHAR(50) DEFAULT 'pending',
                -- Status: 'pending', 'approved', 'rejected', 'kb_created'

                reviewed_by NVARCHAR(200),
                reviewed_date DATETIME2,
                notes NVARCHAR(MAX),

                created_at DATETIME2 DEFAULT GETDATE(),
                updated_at DATETIME2 DEFAULT GETDATE()
            )
        ''')
        print("✅ engineer_reports table created")

        print("Creating kb_update_requests table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'kb_update_requests')
            CREATE TABLE kb_update_requests (
                id INT IDENTITY(1,1) PRIMARY KEY,
                kb_article_id NVARCHAR(50),
                kb_article_title NVARCHAR(500),
                product NVARCHAR(100),
                issue_description NVARCHAR(MAX),
                new_troubleshooting NVARCHAR(MAX),
                submitted_by NVARCHAR(200),
                submitted_date DATETIME2 DEFAULT GETDATE(),
                status NVARCHAR(50) DEFAULT 'pending',
                -- Status: 'pending', 'approved', 'rejected', 'implemented'
                priority NVARCHAR(20),
                related_report_ids NVARCHAR(500),
                reviewed_by NVARCHAR(200),
                reviewed_date DATETIME2,
                notes NVARCHAR(MAX)
            )
        ''')
        print("✅ kb_update_requests table created")

        print("Creating new_kb_requests table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'new_kb_requests')
            CREATE TABLE new_kb_requests (
                id INT IDENTITY(1,1) PRIMARY KEY,
                issue_title NVARCHAR(500),
                product NVARCHAR(100),
                issue_description NVARCHAR(MAX),
                troubleshooting_steps NVARCHAR(MAX),
                submitted_by NVARCHAR(200),
                submitted_date DATETIME2 DEFAULT GETDATE(),
                status NVARCHAR(50) DEFAULT 'pending',
                -- Status: 'pending', 'approved', 'in_progress', 'completed', 'rejected'
                priority NVARCHAR(20),
                frequency_count INT DEFAULT 1,
                related_report_ids NVARCHAR(500),
                assigned_to NVARCHAR(200),
                kb_created_id NVARCHAR(50),
                reviewed_by NVARCHAR(200),
                reviewed_date DATETIME2,
                notes NVARCHAR(MAX)
            )
        ''')
        print("✅ new_kb_requests table created")

        print("Creating kb_statistics table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'kb_statistics')
            CREATE TABLE kb_statistics (
                kb_article_id NVARCHAR(50) PRIMARY KEY,
                kb_article_title NVARCHAR(500),
                product NVARCHAR(100),
                total_reports INT DEFAULT 0,
                success_count INT DEFAULT 0,
                failed_count INT DEFAULT 0,
                outdated_count INT DEFAULT 0,
                last_reported DATETIME2,
                last_updated DATETIME2 DEFAULT GETDATE()
            )
        ''')
        print("✅ kb_statistics table created")

        print("Creating indexes...")
        # Create indexes
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_product')
            CREATE INDEX idx_product ON engineer_reports(product)
        ''')

        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_kb_id')
            CREATE INDEX idx_kb_id ON engineer_reports(kb_article_id)
        ''')

        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_status')
            CREATE INDEX idx_status ON engineer_reports(status)
        ''')

        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_report_type')
            CREATE INDEX idx_report_type ON engineer_reports(report_type)
        ''')

        print("✅ Indexes created")

    print("\n" + "="*60)
    print("✅ Azure SQL schema created successfully!")
    print("="*60)

def main():
    """Main function"""
    print("\n" + "="*60)
    print("KB ASSIST - Azure SQL Schema Creation")
    print("="*60 + "\n")

    try:
        create_tables()
        print("\n✅ All tables and indexes created successfully!")
        print("\nNext step: Run migrate_to_azure.py to import data from SQLite")
    except Exception as e:
        print(f"\n❌ Error creating schema: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has correct Azure SQL credentials")
        print("2. Verify firewall rules allow your IP address")
        print("3. Test connection with: python azure_db.py")

if __name__ == '__main__':
    main()
