"""
seed_sudo_admin.py
------------------
Run this ONCE to create the first sudo_admin in the database.
Without this you cannot log in to the system at all since there
is no self-registration endpoint.

Usage:
    python seed_sudo_admin.py

After running:
    Email:    superadmin@padhai.com   (or whatever you set below)
    Password: the one you set in SUDO_ADMIN_PASSWORD env var or default below

IMPORTANT:
    - Run this only once. Running again will print "sudo_admin already exists".
    - Change the password after first login via POST /auth/change-password
    - Set SUDO_ADMIN_PASSWORD in your .env before running in production
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from sqlalchemy import select
from src.db.main import AsyncSessionLocal
from src.db.models import User, UserRole
from src.services.db_services.auth_service import hash_password

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()


SUDO_ADMIN_EMAIL = os.getenv("SUDO_ADMIN_EMAIL", "superadmin@padhai.com")
SUDO_ADMIN_PASSWORD = os.getenv("SUDO_ADMIN_PASSWORD", "superAdmin@123")
SUDO_ADMIN_FIRSTNAME = os.getenv("SUDO_ADMIN_FIRSTNAME", "Super")
SUDO_ADMIN_LASTNAME = os.getenv("SUDO_ADMIN_LASTNAME", "Admin")


async def seed():
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(User).where(
                    User.email == SUDO_ADMIN_EMAIL.lower().strip(),
                    User.role == UserRole.sudo_admin,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"✅ sudo_admin already exists: {existing.email}")
                print("   No changes made.")
                return

            sudo_admin = User(
                email=SUDO_ADMIN_EMAIL.lower().strip(),
                password_hash=hash_password(SUDO_ADMIN_PASSWORD),
                first_name=SUDO_ADMIN_FIRSTNAME,
                last_name=SUDO_ADMIN_LASTNAME,
                role=UserRole.sudo_admin,
                school_id=None,  # sudo_admin has no school
                is_active=True,
                is_password_changed=True,  # no banner shown for sudo_admin
            )
            db.add(sudo_admin)
            await db.commit()

            print("✅ sudo_admin created successfully!")
            print(f"   Email:    {SUDO_ADMIN_EMAIL}")
            print(f"   Password: {SUDO_ADMIN_PASSWORD}")
            print()
            print("⚠️  IMPORTANT: Change this password immediately after first login.")
            print("   POST /auth/change-password")

        except Exception as e:
            await db.rollback()
            print(f"❌ Failed to create sudo_admin: {str(e)}")


if __name__ == "__main__":
    asyncio.run(seed())
