-- Quick fix to add email to REQ-000060 for testing
-- Run this SQL on your Azure database

-- Step 1: Add email column to new_kb_requests if it doesn't exist
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'new_kb_requests'
    AND COLUMN_NAME = 'submitted_by_email'
)
BEGIN
    ALTER TABLE new_kb_requests ADD submitted_by_email NVARCHAR(200);
    PRINT 'Column added';
END
ELSE
BEGIN
    PRINT 'Column already exists';
END
GO

-- Step 2: Update REQ-000060 with test email
UPDATE new_kb_requests
SET submitted_by_email = 'definitelynotvoshk@gmail.com'
WHERE request_id = 'REQ-000060';

PRINT 'Email added to REQ-000060';
GO

-- Step 3: Verify
SELECT request_id, submitted_by, submitted_by_email, related_report_ids
FROM new_kb_requests
WHERE request_id = 'REQ-000060';
