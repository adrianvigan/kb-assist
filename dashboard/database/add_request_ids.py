"""
Add Request ID System to KB Assist
Adds unique request IDs to all submissions and creates tracking tables
"""
from azure_db import get_connection_context
from datetime import datetime

def generate_sequential_request_id(counter):
    """Generate sequential request ID (e.g., REQ-000001, REQ-000002)"""
    return f"REQ-{counter:06d}"

def add_request_id_columns():
    """Add request_id columns to existing tables"""
    print("\n📝 Adding request_id columns to tables...")

    with get_connection_context() as conn:
        cursor = conn.cursor()

        # Add request_id to engineer_reports
        print("  Adding to engineer_reports...")
        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('engineer_reports')
                AND name = 'request_id'
            )
            ALTER TABLE engineer_reports
            ADD request_id NVARCHAR(50) NULL
        ''')

        # Add request_id to kb_update_requests
        print("  Adding to kb_update_requests...")
        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('kb_update_requests')
                AND name = 'request_id'
            )
            ALTER TABLE kb_update_requests
            ADD request_id NVARCHAR(50) NULL
        ''')

        # Add request_id to new_kb_requests
        print("  Adding to new_kb_requests...")
        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('new_kb_requests')
                AND name = 'request_id'
            )
            ALTER TABLE new_kb_requests
            ADD request_id NVARCHAR(50) NULL
        ''')

        print("✅ Request ID columns added")

def populate_existing_request_ids():
    """Generate request IDs for existing records"""
    print("\n🔢 Generating Request IDs for existing records...")

    with get_connection_context() as conn:
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

def create_tracking_tables():
    """Create new tables for submission history and feedback"""
    print("\n📊 Creating tracking tables...")

    with get_connection_context() as conn:
        cursor = conn.cursor()

        # Submission History Table
        print("  Creating submission_history table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'submission_history')
            CREATE TABLE submission_history (
                id INT IDENTITY(1,1) PRIMARY KEY,
                request_id NVARCHAR(50) NOT NULL,
                revision_number INT NOT NULL,
                submission_type NVARCHAR(50) NOT NULL, -- 'engineer_report', 'kb_update', 'new_kb'
                original_id INT NOT NULL, -- ID from original table

                -- Snapshot of submission data at this revision
                product NVARCHAR(100),
                issue_description NVARCHAR(MAX),
                troubleshooting_steps NVARCHAR(MAX),
                kb_article_id NVARCHAR(50),
                kb_article_title NVARCHAR(500),

                -- Submission metadata
                submitted_by NVARCHAR(200),
                submitted_by_email NVARCHAR(200),
                submitted_date DATETIME2 DEFAULT GETDATE(),
                status NVARCHAR(50),

                -- Parent tracking
                parent_revision_id INT NULL, -- Links to previous revision

                created_at DATETIME2 DEFAULT GETDATE()
            )
        ''')

        # Feedback History Table
        print("  Creating feedback_history table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'feedback_history')
            CREATE TABLE feedback_history (
                id INT IDENTITY(1,1) PRIMARY KEY,
                request_id NVARCHAR(50) NOT NULL,
                feedback_type NVARCHAR(50) NOT NULL, -- 'rejection', 'approval', 'verification', 'revision_request'

                -- Feedback content
                feedback_text NVARCHAR(MAX),
                kb_link NVARCHAR(500),
                reference_notes NVARCHAR(MAX),

                -- Who gave feedback
                feedback_by NVARCHAR(200),
                feedback_by_email NVARCHAR(200),
                feedback_date DATETIME2 DEFAULT GETDATE(),

                -- Related revision
                revision_number INT,

                created_at DATETIME2 DEFAULT GETDATE()
            )
        ''')

        # Email Notifications Table
        print("  Creating email_notifications table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'email_notifications')
            CREATE TABLE email_notifications (
                id INT IDENTITY(1,1) PRIMARY KEY,
                request_id NVARCHAR(50) NOT NULL,
                email_type NVARCHAR(50) NOT NULL, -- 'rejection', 'approval', 'verification_needed'

                -- Email details
                recipient_email NVARCHAR(200),
                recipient_name NVARCHAR(200),
                subject NVARCHAR(500),
                body NVARCHAR(MAX),

                -- Tracking
                sent_date DATETIME2 DEFAULT GETDATE(),
                sent_successfully BIT DEFAULT 1,
                error_message NVARCHAR(MAX),

                -- Links included in email
                revision_link NVARCHAR(500),
                verification_link NVARCHAR(500),

                created_at DATETIME2 DEFAULT GETDATE()
            )
        ''')

        # Add indexes
        print("  Creating indexes...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_submission_history_request_id')
            CREATE INDEX idx_submission_history_request_id ON submission_history(request_id)
        ''')

        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_feedback_history_request_id')
            CREATE INDEX idx_feedback_history_request_id ON feedback_history(request_id)
        ''')

        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_email_notifications_request_id')
            CREATE INDEX idx_email_notifications_request_id ON email_notifications(request_id)
        ''')

        print("✅ Tracking tables created")

def add_workflow_columns():
    """Add workflow-related columns to existing tables"""
    print("\n🔄 Adding workflow columns...")

    with get_connection_context() as conn:
        cursor = conn.cursor()

        # Add columns to kb_update_requests
        print("  Updating kb_update_requests...")
        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('kb_update_requests')
                AND name = 'revision_number'
            )
            ALTER TABLE kb_update_requests
            ADD revision_number INT DEFAULT 1
        ''')

        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('kb_update_requests')
                AND name = 'approved_kb_link'
            )
            ALTER TABLE kb_update_requests
            ADD approved_kb_link NVARCHAR(500) NULL
        ''')

        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('kb_update_requests')
                AND name = 'engineer_verification_status'
            )
            ALTER TABLE kb_update_requests
            ADD engineer_verification_status NVARCHAR(50) NULL
        ''')

        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('kb_update_requests')
                AND name = 'verification_date'
            )
            ALTER TABLE kb_update_requests
            ADD verification_date DATETIME2 NULL
        ''')

        # Add columns to new_kb_requests
        print("  Updating new_kb_requests...")
        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('new_kb_requests')
                AND name = 'revision_number'
            )
            ALTER TABLE new_kb_requests
            ADD revision_number INT DEFAULT 1
        ''')

        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('new_kb_requests')
                AND name = 'approved_kb_link'
            )
            ALTER TABLE new_kb_requests
            ADD approved_kb_link NVARCHAR(500) NULL
        ''')

        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('new_kb_requests')
                AND name = 'engineer_verification_status'
            )
            ALTER TABLE new_kb_requests
            ADD engineer_verification_status NVARCHAR(50) NULL
        ''')

        cursor.execute('''
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('new_kb_requests')
                AND name = 'verification_date'
            )
            ALTER TABLE new_kb_requests
            ADD verification_date DATETIME2 NULL
        ''')

        print("✅ Workflow columns added")

def main():
    """Main function"""
    print("\n" + "="*60)
    print("KB ASSIST - Request ID System Setup")
    print("="*60)

    try:
        # Step 1: Add request_id columns
        add_request_id_columns()

        # Step 2: Create tracking tables
        create_tracking_tables()

        # Step 3: Add workflow columns
        add_workflow_columns()

        # Step 4: Populate existing records with request IDs
        populate_existing_request_ids()

        print("\n" + "="*60)
        print("✅ Request ID System Setup Complete!")
        print("="*60)
        print("\nNext steps:")
        print("1. Test email notification system")
        print("2. Create engineer portals (revision & verification)")
        print("3. Update dashboard with new features")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
