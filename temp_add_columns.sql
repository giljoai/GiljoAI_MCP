-- Add system_instructions and user_instructions columns to agent_templates

ALTER TABLE agent_templates
ADD COLUMN IF NOT EXISTS system_instructions TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS user_instructions TEXT;

-- Update comment on template_content
COMMENT ON COLUMN agent_templates.template_content IS
'DEPRECATED (v3.1): Use system_instructions + user_instructions. Kept for backward compatibility.';

-- Verify columns added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_templates'
AND column_name IN ('system_instructions', 'user_instructions', 'template_content')
ORDER BY column_name;
