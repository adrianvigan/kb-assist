-- ONE-STEP FIX for REQ-000060
-- Copy and paste this ENTIRE block into Neon.tech console and run it

WITH new_report AS (
    INSERT INTO engineer_reports (
        case_number,
        case_title,
        product,
        engineer_name,
        engineer_email,
        report_type,
        new_troubleshooting,
        created_at
    ) VALUES (
        'TEST-000060',
        'Test Case for REQ-000060',
        'Test Product',
        'Test Engineer',
        'definitelynotvoshk@gmail.com',
        'no_kb_exists',
        'Test troubleshooting steps',
        NOW()
    )
    RETURNING id
)
UPDATE new_kb_requests
SET related_report_ids = (SELECT id::TEXT FROM new_report)
WHERE request_id = 'REQ-000060'
RETURNING request_id, related_report_ids;
