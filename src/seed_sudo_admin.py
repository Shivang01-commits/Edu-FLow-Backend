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

# Ensure the project root (which contains the `src` package) is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

from src.db.main import SessionLocal, init_db
from src.db.models import User, UserRole
from src.services.db_services.auth_service import hash_password

# ---------------------------------------------------------------------------
# Config — change these or set as environment variables
# ---------------------------------------------------------------------------
SUDO_ADMIN_EMAIL = os.getenv("SUDO_ADMIN_EMAIL", "superadmin@padhai.com")
SUDO_ADMIN_PASSWORD = os.getenv("SUDO_ADMIN_PASSWORD", "SuperAdmin@123")
SUDO_ADMIN_FIRSTNAME = os.getenv("SUDO_ADMIN_FIRSTNAME", "Super")
SUDO_ADMIN_LASTNAME = os.getenv("SUDO_ADMIN_LASTNAME", "Admin")


def seed():
    # create tables if they don't exist yet
    init_db()

    db = SessionLocal()
    try:
        # check if sudo_admin already exists
        existing = (
            db.query(User)
            .filter(
                User.email == SUDO_ADMIN_EMAIL.lower().strip(),
                User.role == UserRole.sudo_admin,
            )
            .first()
        )

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
        db.commit()

        print("✅ sudo_admin created successfully!")
        print(f"   Email:    {SUDO_ADMIN_EMAIL}")
        print(f"   Password: {SUDO_ADMIN_PASSWORD}")
        print()
        print("⚠️  IMPORTANT: Change this password immediately after first login.")
        print(f"   POST /auth/change-password")

    except Exception as e:
        db.rollback()
        print(f"❌ Failed to create sudo_admin: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
