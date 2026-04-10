-- Diagnostic queries for REQ-000060
-- Run these one by one in Neon.tech console

-- 1. Check new_kb_requests data
SELECT
    id,
    request_id,
    submitted_by,
    related_report_ids,
    status,
    submitted_date
FROM new_kb_requests
WHERE request_id = 'REQ-000060';

-- 2. If related_report_ids exists, check engineer_reports
SELECT
    er.id,
    er.case_number,
    er.engineer_name,
    er.engineer_email,
    er.created_at
FROM engineer_reports er
WHERE er.id::text IN (
    SELECT related_report_ids
    FROM new_kb_requests
    WHERE request_id = 'REQ-000060'
);

-- 3. Check the JOIN that dashboard uses
SELECT
    nkr.request_id,
    nkr.related_report_ids,
    er.id as engineer_report_id,
    er.engineer_email,
    er.engineer_name
FROM new_kb_requests nkr
LEFT JOIN engineer_reports er ON nkr.related_report_ids = er.id::text
WHERE nkr.request_id = 'REQ-000060';

-- 4. Check if engineer_email column exists in engineer_reports
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'engineer_reports'
AND column_name = 'engineer_email';
