"""Add dual-field columns to all databases."""
import psycopg2

databases = ['giljo_mcp', 'giljo_mcp_test']

for db_name in databases:
    try:
        print(f'\nProcessing database: {db_name}')
        conn = psycopg2.connect(f'postgresql://postgres:***@localhost/{db_name}')
        cur = conn.cursor()

        # Add system_instructions
        cur.execute(
            "ALTER TABLE agent_templates "
            "ADD COLUMN IF NOT EXISTS system_instructions TEXT NOT NULL DEFAULT ''"
        )

        # Add user_instructions
        cur.execute(
            "ALTER TABLE agent_templates "
            "ADD COLUMN IF NOT EXISTS user_instructions TEXT"
        )

        conn.commit()
        cur.close()
        conn.close()
        print(f'  [OK] Added columns to {db_name}')
    except Exception as e:
        if 'does not exist' in str(e):
            print(f'  [SKIP] Database {db_name} does not exist')
        else:
            print(f'  [ERROR] {db_name}: {e}')

print('\n[DONE] Processed all databases')
