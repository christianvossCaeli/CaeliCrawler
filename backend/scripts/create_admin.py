#!/usr/bin/env python3
"""
Script to create an initial admin user.

Usage:
    python scripts/create_admin.py

The script will prompt for email, password, and name interactively.
Or you can set environment variables:
    ADMIN_EMAIL=admin@example.com
    ADMIN_PASSWORD=securepassword
    ADMIN_NAME="Admin User"
"""

import asyncio
import getpass
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.database import async_session_factory, init_db
from app.models.user import User, UserRole


async def create_admin_user(
    email: str,
    password: str,
    full_name: str,
    session: AsyncSession,
) -> User:
    """Create an admin user."""
    # Check if user already exists
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        update = input("Update to admin? [y/N]: ").strip().lower()
        if update == "y":
            existing.role = UserRole.ADMIN
            existing.is_superuser = True
            existing.is_active = True
            await session.commit()
            return existing
        else:
            return existing

    # Create new admin user
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def main():
    """Main function."""

    # Get credentials from environment or prompt
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    full_name = os.environ.get("ADMIN_NAME")

    if not email:
        email = input("Admin Email: ").strip()
        if not email:
            sys.exit(1)

    if not password:
        password = getpass.getpass("Admin Password: ")
        if len(password) < 8:
            sys.exit(1)
        password_confirm = getpass.getpass("Confirm Password: ")
        if password != password_confirm:
            sys.exit(1)

    if not full_name:
        full_name = input("Full Name [Admin]: ").strip() or "Admin"

    # Initialize database
    await init_db()

    # Create admin user
    async with async_session_factory() as session:
        await create_admin_user(email, password, full_name, session)


if __name__ == "__main__":
    asyncio.run(main())
