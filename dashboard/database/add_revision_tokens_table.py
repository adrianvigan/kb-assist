"""
Add revision_tokens table to Azure SQL Database
Stores secure tokens for revision and verification links
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

def create_revision_tokens_table():
    """Create revision_tokens table"""
    print("\n" + "="*60)
    print("Adding revision_tokens Table to Azure SQL")
    print("="*60)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'revision_tokens'
        """)
        exists = cursor.fetchone()[0]

        if exists:
            print("\n⚠️  Table 'revision_tokens' already exists")
            print("Skipping creation...")
            conn.close()
            return

        # Create revision_tokens table
        print("\n📝 Creating revision_tokens table...")
        cursor.execute('''
            CREATE TABLE revision_tokens (
                id INT IDENTITY(1,1) PRIMARY KEY,
                token VARCHAR(255) NOT NULL UNIQUE,
                request_id VARCHAR(20) NOT NULL,
                request_type VARCHAR(20) NOT NULL,
                engineer_email VARCHAR(255) NOT NULL,
                action_type VARCHAR(10) NOT NULL,
                kb_link VARCHAR(500) NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL DEFAULT GETDATE(),
                used BIT NOT NULL DEFAULT 0,
                used_at DATETIME NULL
            )
        ''')

        # Create indexes for faster lookups
        print("📝 Creating indexes...")
        cursor.execute('''
            CREATE INDEX idx_revision_tokens_token
            ON revision_tokens(token)
        ''')
        cursor.execute('''
            CREATE INDEX idx_revision_tokens_request_id
            ON revision_tokens(request_id)
        ''')
        cursor.execute('''
            CREATE INDEX idx_revision_tokens_engineer_email
            ON revision_tokens(engineer_email)
        ''')

        conn.commit()

        print("\n✅ Table 'revision_tokens' created successfully!")
        print("\nTable structure:")
        print("  - id: Auto-incrementing primary key")
        print("  - token: Unique secure token (32 chars)")
        print("  - request_id: Request ID (e.g., REQ-000123)")
        print("  - request_type: 'kb_update' or 'new_kb'")
        print("  - engineer_email: Engineer's email address")
        print("  - action_type: 'revise' or 'verify'")
        print("  - kb_link: Link to KB (for verification tokens)")
        print("  - expires_at: Token expiration datetime")
        print("  - created_at: Token creation datetime")
        print("  - used: Whether token has been used (0/1)")
        print("  - used_at: When token was used")

        print("\n" + "="*60)
        print("✅ Migration completed successfully!")
        print("="*60)

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_revision_tokens_table()
