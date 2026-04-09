"""
Migrate KB Articles from SQLite to PostgreSQL
Copies all scraped KB articles to Neon.tech database
"""
import sqlite3
import sys
import os

# Add database path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard', 'database'))
from azure_db import get_connection

# SQLite database path
SQLITE_DB = os.path.join(os.path.dirname(__file__), 'database', 'kb_assist.db')

def migrate_kb_articles():
    """Migrate all KB articles from SQLite to PostgreSQL"""

    print("="*80)
    print("🔄 KB ARTICLES MIGRATION - SQLite to PostgreSQL")
    print("="*80)

    # Connect to SQLite (source)
    print("\n📂 Connecting to SQLite database...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Count records in SQLite
    sqlite_cursor.execute("SELECT COUNT(*) FROM kb_articles")
    sqlite_count = sqlite_cursor.fetchone()[0]
    print(f"✅ Found {sqlite_count} KB articles in SQLite")

    if sqlite_count == 0:
        print("❌ No KB articles to migrate!")
        return

    # Connect to PostgreSQL (destination)
    print("\n🗄️  Connecting to PostgreSQL database...")
    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    # Check current count in PostgreSQL
    pg_cursor.execute("SELECT COUNT(*) FROM kb_articles")
    pg_count_before = pg_cursor.fetchone()[0]
    print(f"📊 PostgreSQL currently has {pg_count_before} KB articles")

    # Get all KB articles from SQLite
    print("\n📥 Reading KB articles from SQLite...")
    sqlite_cursor.execute("""
        SELECT
            kb_number, title, url, content,
            article_html, product, created_date, last_updated
        FROM kb_articles
    """)

    kb_articles = sqlite_cursor.fetchall()
    print(f"✅ Loaded {len(kb_articles)} KB articles into memory")

    # Insert into PostgreSQL (with conflict handling)
    print("\n📤 Inserting into PostgreSQL...")
    inserted = 0
    skipped = 0

    for idx, article in enumerate(kb_articles, 1):
        kb_number, title, url, content, article_html, product, created_date, last_updated = article

        try:
            pg_cursor.execute("""
                INSERT INTO kb_articles
                (kb_number, title, url, content, article_html, product, created_date, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kb_number) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    content = EXCLUDED.content,
                    article_html = EXCLUDED.article_html,
                    product = EXCLUDED.product,
                    last_updated = EXCLUDED.last_updated
            """, (kb_number, title, url, content, article_html, product, created_date, last_updated))
            inserted += 1
        except Exception as e:
            print(f"⚠️  Error inserting KB-{kb_number}: {e}")
            skipped += 1

        # Progress indicator
        if idx % 100 == 0:
            print(f"   Progress: {idx}/{len(kb_articles)} ({idx/len(kb_articles)*100:.1f}%)")

    # Commit changes
    print("\n💾 Committing to database...")
    pg_conn.commit()

    # Verify final count
    pg_cursor.execute("SELECT COUNT(*) FROM kb_articles")
    pg_count_after = pg_cursor.fetchone()[0]

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    # Summary
    print("\n" + "="*80)
    print("✅ MIGRATION COMPLETE!")
    print("="*80)
    print(f"📊 SQLite:     {sqlite_count} articles")
    print(f"📊 PostgreSQL: {pg_count_after} articles")
    print(f"✅ Inserted:   {inserted} articles")
    print(f"⚠️  Skipped:    {skipped} articles")
    print("="*80)

    # Test a specific KB
    print("\n🧪 Testing KB-11005...")
    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT title, product FROM kb_articles WHERE kb_number = '11005'")
    result = pg_cursor.fetchone()
    if result:
        print(f"✅ KB-11005 found: {result[0]} ({result[1]})")
    else:
        print("❌ KB-11005 NOT found")
    pg_conn.close()

if __name__ == '__main__':
    try:
        migrate_kb_articles()
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
