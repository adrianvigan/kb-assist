-- Quick fix to add email to REQ-000060 for testing
-- Run this SQL on your Azure database

-- Step 1: Find REQ-000060's related engineer report
DECLARE @related_report_id INT;

SELECT @related_report_id = TRY_CAST(related_report_ids AS INT)
FROM new_kb_requests
WHERE request_id = 'REQ-000060';

PRINT 'Related report ID: ' + ISNULL(CAST(@related_report_id AS NVARCHAR), 'NULL');

-- Step 2: Update the engineer_reports table with the email
IF @related_report_id IS NOT NULL
BEGIN
    UPDATE engineer_reports
    SET engineer_email = 'definitelynotvoshk@gmail.com'
    WHERE id = @related_report_id;

    PRINT 'Email updated in engineer_reports';
END
ELSE
BEGIN
    -- No related report - create one
    DECLARE @new_report_id INT;

    INSERT INTO engineer_reports (
        case_number, case_title, product, engineer_name,
        engineer_email, report_type, new_troubleshooting, created_at
    ) VALUES (
        'TEST-CASE-060', 'Test Case for REQ-000060', 'Test Product',
        'Test Engineer', 'definitelynotvoshk@gmail.com',
        'no_kb_exists', 'Test troubleshooting steps', GETDATE()
    );

    SET @new_report_id = SCOPE_IDENTITY();

    -- Link it to REQ-000060
    UPDATE new_kb_requests
    SET related_report_ids = CAST(@new_report_id AS NVARCHAR)
    WHERE request_id = 'REQ-000060';

    PRINT 'Created new engineer_reports entry and linked to REQ-000060';
END

-- Step 3: Verify
SELECT
    nkr.request_id,
    nkr.submitted_by,
    nkr.related_report_ids,
    er.engineer_email
FROM new_kb_requests nkr
LEFT JOIN engineer_reports er ON nkr.related_report_ids = CAST(er.id AS NVARCHAR)
WHERE nkr.request_id = 'REQ-000060';
