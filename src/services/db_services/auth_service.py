"""
auth_service.py
---------------
  - Login (returns access + refresh tokens + is_password_changed flag)
  - Token refresh
  - Get profile
  - Change password (sets is_password_changed = True)

Note: Registration is handled by admin_service.py, not here.
      Only sudo_admin self-registers via a seeding script.
"""

import bcrypt as bcrypt_lib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from src.db.models import User
from src.utils.jwt_handler import create_access_token, create_refresh_token


def hash_password(password: str) -> str:
    return bcrypt_lib.hashpw(password.encode("utf-8"), bcrypt_lib.gensalt()).decode(
        "utf-8"
    )


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _token_keys(role: str) -> tuple[str, str]:
    """
    Returns (access_token_key, refresh_token_key) based on role.
    e.g. "admin" → ("admin_access_token", "admin_refresh_token")
    Handles both enum values like "sudo_admin" and plain strings.
    """
    prefix = role.lower().replace(" ", "_")  # safety normalisation
    return f"{prefix}_access_token", f"{prefix}_refresh_token"


class AuthService:
    # -----------------------------------------------------------------------
    # LOGIN
    # Returns role-prefixed access + refresh tokens + is_password_changed flag.
    # e.g. admin_access_token, admin_refresh_token
    # Frontend checks is_password_changed to show "please change password" banner.
    # -----------------------------------------------------------------------
    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        required_role: str | None = None,
    ) -> dict:
        result = await db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No user found",
            )
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Contact your school administrator.",
            )

        user_role = user.role.value

        if required_role and user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",  # intentionally vague, don't leak role info
            )

        access_token_key, refresh_token_key = _token_keys(user_role)
        access_token = create_access_token(
            user_id=str(user.user_id),
            role=user_role,
            school_id=str(user.school_id) if user.school_id else None,
        )
        refresh_token = create_refresh_token(user_id=str(user.user_id))

        return {
            access_token_key: access_token,
            refresh_token_key: refresh_token,
            "token_type": "bearer",
            "is_password_changed": user.is_password_changed,
            "user": {
                "user_id": str(user.user_id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user_role,
                "school_id": str(user.school_id) if user.school_id else None,
                "is_password_changed": user.is_password_changed,
            },
        }

    # -----------------------------------------------------------------------
    # REFRESH — issue new access token using refresh token
    # No DB access, stays as plain def
    # -----------------------------------------------------------------------
    def refresh_access_token(self, user: User) -> dict:
        user_role = user.role.value
        access_token_key, _ = _token_keys(user_role)

        access_token = create_access_token(
            user_id=str(user.user_id),
            role=user_role,
            school_id=str(user.school_id) if user.school_id else None,
        )
        return {
            access_token_key: access_token,
            "token_type": "bearer",
        }

    # -----------------------------------------------------------------------
    # GET PROFILE — /auth/me
    # No DB access, stays as plain def
    # -----------------------------------------------------------------------
    def get_profile(self, user: User) -> dict:
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "school_id": str(user.school_id) if user.school_id else None,
            "is_active": user.is_active,
            "is_password_changed": user.is_password_changed,
            "created_at": user.created_at,
        }

    # -----------------------------------------------------------------------
    # CHANGE PASSWORD
    # Sets is_password_changed = True after successful change.
    # -----------------------------------------------------------------------
    async def change_password(
        self,
        db: AsyncSession,
        user: User,
        old_password: str,
        new_password: str,
    ) -> dict:
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if old_password == new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from your current password",
            )

        user.password_hash = hash_password(new_password)
        user.is_password_changed = True
        await db.commit()

        return {"message": "Password changed successfully"}
