"""
Add Request IDs to SQLite Database (for local dashboard)
This updates the local SQLite database used by the dashboard
"""
import sqlite3
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils'))

def generate_sequential_request_id(counter):
    """Generate sequential request ID (e.g., REQ-000001)"""
    return f"REQ-{counter:06d}"

SQLITE_DB = 'kb_assist.db'

def add_columns():
    """Add request_id columns to SQLite tables"""
    print("\n📝 Adding request_id columns...")

    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()

    # Add to engineer_reports
    try:
        cursor.execute('ALTER TABLE engineer_reports ADD COLUMN request_id TEXT')
        print("  ✅ Added request_id to engineer_reports")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  ℹ️  request_id already exists in engineer_reports")
        else:
            raise

    # Add to kb_update_requests
    try:
        cursor.execute('ALTER TABLE kb_update_requests ADD COLUMN request_id TEXT')
        print("  ✅ Added request_id to kb_update_requests")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  ℹ️  request_id already exists in kb_update_requests")
        else:
            raise

    # Add to new_kb_requests
    try:
        cursor.execute('ALTER TABLE new_kb_requests ADD COLUMN request_id TEXT')
        print("  ✅ Added request_id to new_kb_requests")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  ℹ️  request_id already exists in new_kb_requests")
        else:
            raise

    conn.commit()
    conn.close()

def populate_request_ids():
    """Generate request IDs for existing records"""
    print("\n🔢 Generating Request IDs for existing records...")

    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()

    # Start counter at 1
    counter = 1

    # Update engineer_reports
    cursor.execute("SELECT COUNT(*) FROM engineer_reports WHERE request_id IS NULL")
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"  Updating {count} engineer reports...")
        cursor.execute("SELECT id FROM engineer_reports WHERE request_id IS NULL ORDER BY id")

        for row in cursor.fetchall():
            request_id = generate_sequential_request_id(counter)
            cursor.execute(
                "UPDATE engineer_reports SET request_id = ? WHERE id = ?",
                (request_id, row[0])
            )
            counter += 1
        print(f"  ✅ Updated {count} engineer reports (REQ-000001 to REQ-{counter-1:06d})")

    # Update kb_update_requests
    cursor.execute("SELECT COUNT(*) FROM kb_update_requests WHERE request_id IS NULL")
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"  Updating {count} KB update requests...")
        cursor.execute("SELECT id FROM kb_update_requests WHERE request_id IS NULL ORDER BY id")

        for row in cursor.fetchall():
            request_id = generate_sequential_request_id(counter)
            cursor.execute(
                "UPDATE kb_update_requests SET request_id = ? WHERE id = ?",
                (request_id, row[0])
            )
            counter += 1
        print(f"  ✅ Updated {count} KB update requests")

    # Update new_kb_requests
    cursor.execute("SELECT COUNT(*) FROM new_kb_requests WHERE request_id IS NULL")
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"  Updating {count} new KB requests...")
        cursor.execute("SELECT id FROM new_kb_requests WHERE request_id IS NULL ORDER BY id")

        for row in cursor.fetchall():
            request_id = generate_sequential_request_id(counter)
            cursor.execute(
                "UPDATE new_kb_requests SET request_id = ? WHERE id = ?",
                (request_id, row[0])
            )
            counter += 1
        print(f"  ✅ Updated {count} new KB requests")

    print(f"\n  Total Request IDs generated: {counter - 1}")

    conn.commit()
    conn.close()

def verify():
    """Verify request IDs were added"""
    print("\n🔍 Verifying...")

    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()

    # Check a few sample records
    cursor.execute("SELECT id, request_id FROM engineer_reports LIMIT 5")
    print("\nSample engineer_reports:")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]}")

    cursor.execute("SELECT id, request_id FROM kb_update_requests LIMIT 3")
    print("\nSample kb_update_requests:")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]}")

    cursor.execute("SELECT id, request_id FROM new_kb_requests LIMIT 3")
    print("\nSample new_kb_requests:")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]}")

    conn.close()

def main():
    """Main function"""
    print("\n" + "="*60)
    print("KB ASSIST - Add Request IDs to SQLite")
    print("="*60)

    if not os.path.exists(SQLITE_DB):
        print(f"\n❌ Error: {SQLITE_DB} not found!")
        print("Make sure you're in the database/ directory")
        return

    try:
        add_columns()
        populate_request_ids()
        verify()

        print("\n" + "="*60)
        print("✅ SQLite Database Updated!")
        print("="*60)
        print("\nYou can now see request IDs in the dashboard!")
        print("\nRefresh your dashboard to see the changes.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
