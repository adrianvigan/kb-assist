-- FORCE INSERT email for REQ-000060
-- This creates a new engineer_reports entry and links it
-- Run this in Neon.tech console

-- Step 1: Create engineer_reports entry with email
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
    'Test troubleshooting steps for REQ-000060',
    NOW()
)
RETURNING id;

-- Copy the ID from above, then run this (replace XXX with the ID):
-- UPDATE new_kb_requests SET related_report_ids = 'XXX' WHERE request_id = 'REQ-000060';
