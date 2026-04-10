-- Add revision tracking columns to new_kb_requests table
-- This makes Pending New TS work exactly like Pending KB Updates
-- Run this in Neon.tech console

-- Add revision_number column
ALTER TABLE new_kb_requests
ADD COLUMN IF NOT EXISTS revision_number INT DEFAULT 0;

-- Add original_request_id column
ALTER TABLE new_kb_requests
ADD COLUMN IF NOT EXISTS original_request_id VARCHAR(50);

-- Add parent_request_id column
ALTER TABLE new_kb_requests
ADD COLUMN IF NOT EXISTS parent_request_id INT;

-- Initialize existing records
UPDATE new_kb_requests
SET revision_number = 0,
    original_request_id = request_id
WHERE revision_number IS NULL OR original_request_id IS NULL;

-- Verify
SELECT
    COUNT(*) as total_requests,
    SUM(CASE WHEN revision_number = 0 THEN 1 ELSE 0 END) as originals,
    SUM(CASE WHEN revision_number > 0 THEN 1 ELSE 0 END) as revisions
FROM new_kb_requests;
