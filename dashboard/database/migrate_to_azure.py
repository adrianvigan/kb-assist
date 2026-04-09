"""
Migrate Data from SQLite to Azure SQL Database
Transfers all existing KB Assist data to Azure SQL
"""
import sqlite3
from azure_db import get_connection_context
from datetime import datetime

SQLITE_DB = 'kb_assist.db'

def migrate_engineer_reports():
    """Migrate engineer_reports table"""
    print("\n📊 Migrating engineer_reports...")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Get all reports from SQLite
    sqlite_cursor.execute('SELECT * FROM engineer_reports')
    reports = sqlite_cursor.fetchall()

    print(f"Found {len(reports)} reports in SQLite")

    if len(reports) == 0:
        print("⚠️ No data to migrate")
        sqlite_conn.close()
        return

    # Get column names
    sqlite_cursor.execute('PRAGMA table_info(engineer_reports)')
    columns = [col[1] for col in sqlite_cursor.fetchall()]

    # Connect to Azure SQL
    with get_connection_context() as azure_conn:
        azure_cursor = azure_conn.cursor()

        # Clear existing data (optional - comment out to keep existing data)
        print("Clearing existing Azure SQL data...")
        azure_cursor.execute('DELETE FROM engineer_reports')

        # Insert data
        insert_query = '''
            INSERT INTO engineer_reports (
                report_date, case_number, kb_article_id, kb_article_title,
                product, report_type, what_failed, steps_that_failed,
                new_troubleshooting, new_ts_steps, engineer_name, engineer_email,
                customer_environment, resolution_time, status, reviewed_by,
                reviewed_date, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        count = 0
        for report in reports:
            # Skip the ID (first column) - Azure will auto-generate
            azure_cursor.execute(insert_query, report[1:])
            count += 1

            if count % 50 == 0:
                print(f"  Migrated {count} reports...")

    print(f"✅ Migrated {count} engineer reports")
    sqlite_conn.close()

def migrate_kb_update_requests():
    """Migrate kb_update_requests table"""
    print("\n🔄 Migrating kb_update_requests...")

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute('SELECT * FROM kb_update_requests')
    requests = sqlite_cursor.fetchall()

    print(f"Found {len(requests)} KB update requests in SQLite")

    if len(requests) == 0:
        print("⚠️ No data to migrate")
        sqlite_conn.close()
        return

    with get_connection_context() as azure_conn:
        azure_cursor = azure_conn.cursor()

        print("Clearing existing Azure SQL data...")
        azure_cursor.execute('DELETE FROM kb_update_requests')

        insert_query = '''
            INSERT INTO kb_update_requests (
                kb_article_id, kb_article_title, product, issue_description,
                new_troubleshooting, submitted_by, submitted_date, status,
                priority, related_report_ids, reviewed_by, reviewed_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        count = 0
        for req in requests:
            azure_cursor.execute(insert_query, req[1:])
            count += 1

    print(f"✅ Migrated {count} KB update requests")
    sqlite_conn.close()

def migrate_new_kb_requests():
    """Migrate new_kb_requests table"""
    print("\n➕ Migrating new_kb_requests...")

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute('SELECT * FROM new_kb_requests')
    requests = sqlite_cursor.fetchall()

    print(f"Found {len(requests)} new KB requests in SQLite")

    if len(requests) == 0:
        print("⚠️ No data to migrate")
        sqlite_conn.close()
        return

    with get_connection_context() as azure_conn:
        azure_cursor = azure_conn.cursor()

        print("Clearing existing Azure SQL data...")
        azure_cursor.execute('DELETE FROM new_kb_requests')

        insert_query = '''
            INSERT INTO new_kb_requests (
                issue_title, product, issue_description, troubleshooting_steps,
                submitted_by, submitted_date, status, priority, frequency_count,
                related_report_ids, assigned_to, kb_created_id, reviewed_by,
                reviewed_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        count = 0
        for req in requests:
            azure_cursor.execute(insert_query, req[1:])
            count += 1

    print(f"✅ Migrated {count} new KB requests")
    sqlite_conn.close()

def migrate_kb_statistics():
    """Migrate kb_statistics table"""
    print("\n📈 Migrating kb_statistics...")

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute('SELECT * FROM kb_statistics')
    stats = sqlite_cursor.fetchall()

    print(f"Found {len(stats)} KB statistics in SQLite")

    if len(stats) == 0:
        print("⚠️ No data to migrate")
        sqlite_conn.close()
        return

    with get_connection_context() as azure_conn:
        azure_cursor = azure_conn.cursor()

        print("Clearing existing Azure SQL data...")
        azure_cursor.execute('DELETE FROM kb_statistics')

        insert_query = '''
            INSERT INTO kb_statistics (
                kb_article_id, kb_article_title, product, total_reports,
                success_count, failed_count, outdated_count, last_reported,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        count = 0
        for stat in stats:
            azure_cursor.execute(insert_query, stat)
            count += 1

    print(f"✅ Migrated {count} KB statistics")
    sqlite_conn.close()

def verify_migration():
    """Verify data migration was successful"""
    print("\n🔍 Verifying migration...")

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    with get_connection_context() as azure_conn:
        azure_cursor = azure_conn.cursor()

        # Check engineer_reports
        sqlite_cursor.execute('SELECT COUNT(*) FROM engineer_reports')
        sqlite_count = sqlite_cursor.fetchone()[0]

        azure_cursor.execute('SELECT COUNT(*) FROM engineer_reports')
        azure_count = azure_cursor.fetchone()[0]

        print(f"\nEngineer Reports:")
        print(f"  SQLite: {sqlite_count}")
        print(f"  Azure SQL: {azure_count}")
        print(f"  {'✅ Match!' if sqlite_count == azure_count else '❌ Mismatch!'}")

        # Check kb_update_requests
        sqlite_cursor.execute('SELECT COUNT(*) FROM kb_update_requests')
        sqlite_count = sqlite_cursor.fetchone()[0]

        azure_cursor.execute('SELECT COUNT(*) FROM kb_update_requests')
        azure_count = azure_cursor.fetchone()[0]

        print(f"\nKB Update Requests:")
        print(f"  SQLite: {sqlite_count}")
        print(f"  Azure SQL: {azure_count}")
        print(f"  {'✅ Match!' if sqlite_count == azure_count else '❌ Mismatch!'}")

        # Check new_kb_requests
        sqlite_cursor.execute('SELECT COUNT(*) FROM new_kb_requests')
        sqlite_count = sqlite_cursor.fetchone()[0]

        azure_cursor.execute('SELECT COUNT(*) FROM new_kb_requests')
        azure_count = azure_cursor.fetchone()[0]

        print(f"\nNew KB Requests:")
        print(f"  SQLite: {sqlite_count}")
        print(f"  Azure SQL: {azure_count}")
        print(f"  {'✅ Match!' if sqlite_count == azure_count else '❌ Mismatch!'}")

    sqlite_conn.close()

def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("KB ASSIST - Data Migration to Azure SQL")
    print("="*60)

    try:
        # Migrate all tables
        migrate_engineer_reports()
        migrate_kb_update_requests()
        migrate_new_kb_requests()
        migrate_kb_statistics()

        # Verify migration
        verify_migration()

        print("\n" + "="*60)
        print("✅ Migration completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Update cloud_api.py to use Azure SQL")
        print("2. Update dashboard to use Azure SQL")
        print("3. Test the system end-to-end")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure create_azure_schema.py was run first")
        print("2. Check .env file has correct credentials")
        print("3. Verify firewall rules allow your IP")

if __name__ == '__main__':
    main()
