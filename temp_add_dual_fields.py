"""Temporary script to add system_instructions and user_instructions columns."""
import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:4010@localhost/giljo_mcp')
    cur = conn.cursor()

    print("Adding system_instructions column...")
    cur.execute(
        "ALTER TABLE agent_templates "
        "ADD COLUMN IF NOT EXISTS system_instructions TEXT NOT NULL DEFAULT ''"
    )
    print("[OK] Added system_instructions")

    print("Adding user_instructions column...")
    cur.execute(
        "ALTER TABLE agent_templates "
        "ADD COLUMN IF NOT EXISTS user_instructions TEXT"
    )
    print("[OK] Added user_instructions")

    conn.commit()
    print("[OK] Committed changes")

    # Verify
    print("\nVerifying columns...")
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'agent_templates'
        AND column_name IN ('system_instructions', 'user_instructions', 'template_content')
        ORDER BY column_name
    """)

    results = cur.fetchall()
    print("Columns in agent_templates:")
    for row in results:
        print(f"  - {row[0]}: {row[1]} (nullable={row[2]})")

    cur.close()
    conn.close()
    print("\n[SUCCESS] Dual-field columns added to database.")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
