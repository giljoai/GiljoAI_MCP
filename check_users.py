#!/usr/bin/env python
"""Quick script to check users in database."""

import asyncio

from sqlalchemy import text

from src.giljo_mcp.database import DatabaseManager


DATABASE_URL = "postgresql://giljo_user:0Ek3rVwg3FOOj8j6Pm7I@localhost:5432/giljo_mcp"


async def main():
    db = DatabaseManager(DATABASE_URL, is_async=True)

    async with db.get_session_async() as session:
        result = await session.execute(text("SELECT id, username, email, role, is_system_user FROM users"))
        users = result.fetchall()

        print("\n" + "=" * 100)
        print("CURRENT USERS IN DATABASE:")
        print("=" * 100)
        if len(users) == 0:
            print(">>> NO USERS FOUND - Fresh database! Need to create admin user <<<")
        else:
            for user in users:
                print(
                    f"User ID: {user[0]} | Username: {user[1]} | Email: {user[2]} | Role: {user[3]} | System: {user[4]}"
                )
        print("=" * 100)
        print(f"Total: {len(users)} users\n")


if __name__ == "__main__":
    asyncio.run(main())
