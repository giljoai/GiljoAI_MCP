"""Update test database schema to match current models."""

from sqlalchemy import create_engine, text


engine = create_engine("postgresql://postgres:***@localhost/giljo_mcp_test")

with engine.connect() as conn:
    # Add missing Product columns
    conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS project_path VARCHAR(500)"))
    conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))

    # Add missing Project columns
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS description TEXT"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS orchestrator_summary TEXT"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS closeout_prompt TEXT"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS closeout_executed_at TIMESTAMP WITH TIME ZONE"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS closeout_checklist JSONB"))

    conn.commit()
    print("Test database schema updated successfully")
