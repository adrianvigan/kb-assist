"""
Create kb_articles table in PostgreSQL
"""
import sys
import os

# Add database path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard', 'database'))
from azure_db import get_connection

def create_kb_articles_table():
    """Create kb_articles table in PostgreSQL"""

    print("="*80)
    print("🔧 CREATING kb_articles TABLE IN POSTGRESQL")
    print("="*80)

    conn = get_connection()
    cursor = conn.cursor()

    print("\n📋 Creating table schema...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_articles (
            id SERIAL PRIMARY KEY,
            kb_number VARCHAR(20) UNIQUE NOT NULL,
            title TEXT,
            url TEXT,
            content TEXT,
            article_html TEXT,
            product VARCHAR(100),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("✅ Table created successfully!")

    # Create index for faster lookups
    print("\n📊 Creating indexes...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_kb_articles_kb_number
        ON kb_articles(kb_number)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_kb_articles_product
        ON kb_articles(product)
    """)

    print("✅ Indexes created successfully!")

    conn.commit()
    conn.close()

    print("\n" + "="*80)
    print("✅ SETUP COMPLETE!")
    print("="*80)
    print("You can now run: MIGRATE_KB_ARTICLES.bat")
    print("="*80)

if __name__ == '__main__':
    try:
        create_kb_articles_table()
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
