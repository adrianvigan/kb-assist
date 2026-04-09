"""
Add feedback and verification columns to Azure SQL Database
Required for Phase 2 email workflow
"""
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Create Azure SQL connection"""
    server = os.getenv('AZURE_SQL_SERVER')
    database = os.getenv('AZURE_SQL_DATABASE')
    username = os.getenv('AZURE_SQL_USERNAME')
    password = os.getenv('AZURE_SQL_PASSWORD')
    driver = os.getenv('AZURE_SQL_DRIVER', 'ODBC Driver 18 for SQL Server')

    connection_string = (
        f'DRIVER={{{driver}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
        f'Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    )

    return pyodbc.connect(connection_string)

def add_feedback_columns():
    """Add feedback and verification columns to kb_update_requests and new_kb_requests"""
    print("\n" + "="*60)
    print("Adding Feedback and Verification Columns to Azure SQL")
    print("="*60)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Columns to add
        columns_to_add = [
            ('kb_update_requests', 'feedback_text', 'NVARCHAR(MAX) NULL'),
            ('kb_update_requests', 'kb_link', 'VARCHAR(500) NULL'),
            ('kb_update_requests', 'verification_status', 'VARCHAR(20) NULL'),
            ('kb_update_requests', 'verification_comments', 'NVARCHAR(MAX) NULL'),
            ('kb_update_requests', 'verified_date', 'DATETIME NULL'),
            ('new_kb_requests', 'feedback_text', 'NVARCHAR(MAX) NULL'),
            ('new_kb_requests', 'kb_link', 'VARCHAR(500) NULL'),
            ('new_kb_requests', 'verification_status', 'VARCHAR(20) NULL'),
            ('new_kb_requests', 'verification_comments', 'NVARCHAR(MAX) NULL'),
            ('new_kb_requests', 'verified_date', 'DATETIME NULL'),
        ]

        for table_name, column_name, column_def in columns_to_add:
            # Check if column exists
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
                AND COLUMN_NAME = '{column_name}'
            """)
            exists = cursor.fetchone()[0]

            if exists:
                print(f"\n⏭️  Column '{table_name}.{column_name}' already exists, skipping...")
            else:
                print(f"\n📝 Adding column '{table_name}.{column_name}'...")
                cursor.execute(f"""
                    ALTER TABLE {table_name}
                    ADD {column_name} {column_def}
                """)
                conn.commit()
                print(f"✅ Column '{table_name}.{column_name}' added successfully!")

        print("\n" + "="*60)
        print("✅ Migration completed successfully!")
        print("="*60)

        print("\nColumns added:")
        print("  kb_update_requests:")
        print("    - feedback_text (manager's rejection feedback)")
        print("    - kb_link (approved KB article link)")
        print("    - verification_status (engineer's verification status)")
        print("    - verification_comments (engineer's verification comments)")
        print("    - verified_date (when engineer verified)")
        print("\n  new_kb_requests:")
        print("    - feedback_text (manager's rejection feedback)")
        print("    - kb_link (approved KB article link)")
        print("    - verification_status (engineer's verification status)")
        print("    - verification_comments (engineer's verification comments)")
        print("    - verified_date (when engineer verified)")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    add_feedback_columns()
