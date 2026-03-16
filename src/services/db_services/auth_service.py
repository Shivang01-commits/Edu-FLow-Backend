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
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.db.models import User
from src.utils.jwt_handler import create_access_token, create_refresh_token


def hash_password(password: str) -> str:
    return bcrypt_lib.hashpw(password.encode("utf-8"), bcrypt_lib.gensalt()).decode(
        "utf-8"
    )


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


class AuthService:
    # -----------------------------------------------------------------------
    # LOGIN
    # Returns access token + refresh token + is_password_changed flag.
    # Frontend checks is_password_changed to show "please change password" banner.
    # -----------------------------------------------------------------------
    def login(self, db: Session, email: str, password: str) -> dict:
        user = db.query(User).filter(User.email == email.lower().strip()).first()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Contact your school administrator.",
            )

        access_token = create_access_token(
            user_id=str(user.user_id),
            role=user.role.value,
            school_id=str(user.school_id) if user.school_id else None,
        )
        refresh_token = create_refresh_token(user_id=str(user.user_id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "is_password_changed": user.is_password_changed,
            # Frontend uses this flag:
            # False → show "Please change your default password" banner
            # True  → normal dashboard
            "user": {
                "user_id": str(user.user_id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "school_id": str(user.school_id) if user.school_id else None,
                "is_password_changed": user.is_password_changed,
            },
        }

    # -----------------------------------------------------------------------
    # REFRESH — issue new access token using refresh token
    # -----------------------------------------------------------------------
    def refresh_access_token(self, user: User) -> dict:
        access_token = create_access_token(
            user_id=str(user.user_id),
            role=user.role.value,
            school_id=str(user.school_id) if user.school_id else None,
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    # -----------------------------------------------------------------------
    # GET PROFILE — /auth/me
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
    def change_password(
        self,
        db: Session,
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
        user.is_password_changed = True  # banner goes away on frontend
        db.commit()

        return {"message": "Password changed successfully"}
