"""
Migrate all data from SQLite to PostgreSQL (Neon.tech)
Transfers all existing KB Assist data to the cloud database
"""
import sqlite3
from azure_db import get_connection
from datetime import datetime

SQLITE_DB = 'kb_assist.db'  # Will look in current directory

def migrate_engineer_reports():
    """Migrate engineer_reports table"""
    print("\n" + "="*60)
    print("Migrating engineer_reports...")
    print("="*60)

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Get all reports from SQLite
    sqlite_cursor.execute('SELECT * FROM engineer_reports')
    reports = sqlite_cursor.fetchall()

    print(f"Found {len(reports)} reports in SQLite")

    if len(reports) == 0:
        print("No data to migrate")
        sqlite_conn.close()
        return

    # Get column names
    sqlite_cursor.execute('PRAGMA table_info(engineer_reports)')
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    print(f"Columns: {', '.join(columns)}")

    # Connect to PostgreSQL
    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    # Clear existing data
    print("Clearing existing PostgreSQL data...")
    pg_cursor.execute('DELETE FROM engineer_reports')
    pg_conn.commit()

    # Insert data
    print("Inserting data into PostgreSQL...")

    count = 0
    for report in reports:
        # Skip the ID (first column) - PostgreSQL will auto-generate
        data = list(report[1:])

        # Create placeholders for PostgreSQL (%s instead of ?)
        placeholders = ', '.join(['%s'] * len(data))

        # Build column list (excluding 'id')
        cols = ', '.join(columns[1:])

        insert_query = f'''
            INSERT INTO engineer_reports ({cols})
            VALUES ({placeholders})
        '''

        try:
            pg_cursor.execute(insert_query, data)
            count += 1

            if count % 100 == 0:
                print(f"  Migrated {count} reports...")
                pg_conn.commit()
        except Exception as e:
            print(f"Error migrating report {count+1}: {e}")
            print(f"Data: {data[:5]}...")  # Print first 5 fields for debugging
            continue

    pg_conn.commit()
    print(f"Successfully migrated {count} engineer reports")

    sqlite_conn.close()
    pg_conn.close()

def migrate_kb_update_requests():
    """Migrate kb_update_requests table"""
    print("\n" + "="*60)
    print("Migrating kb_update_requests...")
    print("="*60)

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Check if table exists
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kb_update_requests'")
    if not sqlite_cursor.fetchone():
        print("Table kb_update_requests does not exist in SQLite")
        sqlite_conn.close()
        return

    sqlite_cursor.execute('SELECT * FROM kb_update_requests')
    requests = sqlite_cursor.fetchall()

    print(f"Found {len(requests)} KB update requests in SQLite")

    if len(requests) == 0:
        print("No data to migrate")
        sqlite_conn.close()
        return

    # Get column names
    sqlite_cursor.execute('PRAGMA table_info(kb_update_requests)')
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    print(f"Columns: {', '.join(columns)}")

    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    print("Clearing existing PostgreSQL data...")
    pg_cursor.execute('DELETE FROM kb_update_requests')
    pg_conn.commit()

    print("Inserting data into PostgreSQL...")

    count = 0
    for req in requests:
        data = list(req[1:])  # Skip ID
        placeholders = ', '.join(['%s'] * len(data))
        cols = ', '.join(columns[1:])

        insert_query = f'''
            INSERT INTO kb_update_requests ({cols})
            VALUES ({placeholders})
        '''

        try:
            pg_cursor.execute(insert_query, data)
            count += 1

            if count % 50 == 0:
                print(f"  Migrated {count} requests...")
                pg_conn.commit()
        except Exception as e:
            print(f"Error migrating request {count+1}: {e}")
            continue

    pg_conn.commit()
    print(f"SUCCESS: Successfully migrated {count} KB update requests")

    sqlite_conn.close()
    pg_conn.close()

def migrate_new_kb_requests():
    """Migrate new_kb_requests table"""
    print("\n" + "="*60)
    print("Migrating new_kb_requests...")
    print("="*60)

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Check if table exists
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_kb_requests'")
    if not sqlite_cursor.fetchone():
        print("Table new_kb_requests does not exist in SQLite")
        sqlite_conn.close()
        return

    sqlite_cursor.execute('SELECT * FROM new_kb_requests')
    requests = sqlite_cursor.fetchall()

    print(f"Found {len(requests)} new KB requests in SQLite")

    if len(requests) == 0:
        print("No data to migrate")
        sqlite_conn.close()
        return

    # Get column names
    sqlite_cursor.execute('PRAGMA table_info(new_kb_requests)')
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    print(f"Columns: {', '.join(columns)}")

    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    print("Clearing existing PostgreSQL data...")
    pg_cursor.execute('DELETE FROM new_kb_requests')
    pg_conn.commit()

    print("Inserting data into PostgreSQL...")

    count = 0
    for req in requests:
        data = list(req[1:])  # Skip ID
        placeholders = ', '.join(['%s'] * len(data))
        cols = ', '.join(columns[1:])

        insert_query = f'''
            INSERT INTO new_kb_requests ({cols})
            VALUES ({placeholders})
        '''

        try:
            pg_cursor.execute(insert_query, data)
            count += 1

            if count % 50 == 0:
                print(f"  Migrated {count} requests...")
                pg_conn.commit()
        except Exception as e:
            print(f"Error migrating request {count+1}: {e}")
            continue

    pg_conn.commit()
    print(f"SUCCESS: Successfully migrated {count} new KB requests")

    sqlite_conn.close()
    pg_conn.close()

def migrate_kb_statistics():
    """Migrate kb_statistics table"""
    print("\n" + "="*60)
    print("Migrating kb_statistics...")
    print("="*60)

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Check if table exists
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kb_statistics'")
    if not sqlite_cursor.fetchone():
        print("Table kb_statistics does not exist in SQLite")
        sqlite_conn.close()
        return

    sqlite_cursor.execute('SELECT * FROM kb_statistics')
    stats = sqlite_cursor.fetchall()

    print(f"Found {len(stats)} KB statistics records in SQLite")

    if len(stats) == 0:
        print("No data to migrate")
        sqlite_conn.close()
        return

    # Get column names
    sqlite_cursor.execute('PRAGMA table_info(kb_statistics)')
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    print(f"Columns: {', '.join(columns)}")

    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    print("Clearing existing PostgreSQL data...")
    pg_cursor.execute('DELETE FROM kb_statistics')
    pg_conn.commit()

    print("Inserting data into PostgreSQL...")

    count = 0
    for stat in stats:
        # kb_statistics uses kb_article_id as primary key, so we include all columns
        data = list(stat)
        placeholders = ', '.join(['%s'] * len(data))
        cols = ', '.join(columns)

        insert_query = f'''
            INSERT INTO kb_statistics ({cols})
            VALUES ({placeholders})
            ON CONFLICT (kb_article_id) DO UPDATE SET
                kb_article_title = EXCLUDED.kb_article_title,
                product = EXCLUDED.product,
                total_reports = EXCLUDED.total_reports,
                success_count = EXCLUDED.success_count,
                failed_count = EXCLUDED.failed_count,
                outdated_count = EXCLUDED.outdated_count,
                last_reported = EXCLUDED.last_reported,
                last_updated = EXCLUDED.last_updated
        '''

        try:
            pg_cursor.execute(insert_query, data)
            count += 1

            if count % 50 == 0:
                print(f"  Migrated {count} statistics...")
                pg_conn.commit()
        except Exception as e:
            print(f"Error migrating statistic {count+1}: {e}")
            continue

    pg_conn.commit()
    print(f"SUCCESS: Successfully migrated {count} KB statistics records")

    sqlite_conn.close()
    pg_conn.close()

def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("KB ASSIST - SQLite to PostgreSQL Migration")
    print("="*60)
    print(f"SQLite DB: {SQLITE_DB}")
    print(f"Target: Neon.tech PostgreSQL (FREE)")
    print("="*60)

    try:
        # Migrate all tables
        migrate_engineer_reports()
        migrate_kb_update_requests()
        migrate_new_kb_requests()
        migrate_kb_statistics()

        print("\n" + "="*60)
        print("SUCCESS: MIGRATION COMPLETE!")
        print("="*60)
        print("\nAll your testing data has been migrated to PostgreSQL.")
        print("Your Streamlit dashboard will now show all the real data!")
        print("\nNext step: Reboot your Streamlit app to see the data.")

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Check that SQLite database exists")
        print("2. Verify PostgreSQL connection is working")
        print("3. Check that all tables exist in PostgreSQL")

if __name__ == '__main__':
    main()
