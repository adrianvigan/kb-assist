-- Add AI matching columns to kb_update_requests table
-- This matches the columns in new_kb_requests table

-- Add suggested_kbs column (stores JSON array of AI-suggested matches)
ALTER TABLE kb_update_requests
ADD COLUMN IF NOT EXISTS suggested_kbs TEXT;

-- Add ai_match_status column (tracks AI processing: null, 'processing', 'complete')
ALTER TABLE kb_update_requests
ADD COLUMN IF NOT EXISTS ai_match_status VARCHAR(20);

-- Add ai_processed_at column (timestamp when AI processing completed)
ALTER TABLE kb_update_requests
ADD COLUMN IF NOT EXISTS ai_processed_at TIMESTAMP;

-- Verify columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'kb_update_requests'
AND column_name IN ('suggested_kbs', 'ai_match_status', 'ai_processed_at')
ORDER BY column_name;
