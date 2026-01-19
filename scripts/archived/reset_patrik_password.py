#!/usr/bin/env python3
"""Reset patrik's password for testing."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from src.giljo_mcp.config_manager import ConfigManager
from src.giljo_mcp.models.auth import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def reset_password():
    """Reset patrik's password to TestPass123."""
    config = ConfigManager()
    db_url = config.get_database_url().replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get patrik user
        result = await session.execute(
            select(User).where(User.username == 'patrik')
        )
        user = result.scalar_one_or_none()

        if not user:
            print("ERROR: User 'patrik' not found!")
            return False

        # Hash new password
        new_password_hash = pwd_context.hash("TestPass123")

        # Update password
        await session.execute(
            update(User)
            .where(User.username == 'patrik')
            .values(password_hash=new_password_hash)
        )
        await session.commit()

        print("SUCCESS: Password reset to 'TestPass123' for user 'patrik'")
        return True


if __name__ == "__main__":
    asyncio.run(reset_password())
