-- Force add email definitelynotvoshk@gmail.com to REQ-000060
-- Run this SQL on your PostgreSQL database

-- Step 1: Find the related engineer_reports ID for REQ-000060
DO $$
DECLARE
    report_id INT;
BEGIN
    -- Get the related_report_ids from new_kb_requests
    SELECT related_report_ids::INT INTO report_id
    FROM new_kb_requests
    WHERE request_id = 'REQ-000060';

    -- Update the engineer_reports table with the email
    IF report_id IS NOT NULL THEN
        UPDATE engineer_reports
        SET engineer_email = 'definitelynotvoshk@gmail.com'
        WHERE id = report_id;

        RAISE NOTICE 'Updated engineer_reports.id = % with email', report_id;
    ELSE
        RAISE NOTICE 'No related_report_ids found for REQ-000060';

        -- Create a new engineer_reports entry and link it
        INSERT INTO engineer_reports (
            case_number, case_title, product, engineer_name,
            engineer_email, report_type, new_troubleshooting, created_at
        ) VALUES (
            'TEST-060', 'Test for REQ-000060', 'Test Product',
            'Test Engineer', 'definitelynotvoshk@gmail.com',
            'no_kb_exists', 'Test troubleshooting steps', NOW()
        )
        RETURNING id INTO report_id;

        -- Link it to REQ-000060
        UPDATE new_kb_requests
        SET related_report_ids = report_id::TEXT
        WHERE request_id = 'REQ-000060';

        RAISE NOTICE 'Created new engineer_reports.id = % and linked to REQ-000060', report_id;
    END IF;
END $$;

-- Step 2: Verify the update
SELECT
    nkr.request_id,
    nkr.submitted_by,
    nkr.related_report_ids,
    er.engineer_email,
    er.engineer_name
FROM new_kb_requests nkr
LEFT JOIN engineer_reports er ON nkr.related_report_ids = er.id::text
WHERE nkr.request_id = 'REQ-000060';
