"""
NOTE: Registration is NOT here.
        Teachers and students are registered by admin via /admin/teachers/register
        and /admin/students/register. There is no self-registration.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.models.auth_schema import LoginRequest, ChangePasswordRequest
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.auth_service import AuthService
from src.utils.jwt_handler import get_current_user, get_refresh_token_user

router = APIRouter(prefix="/auth", tags=["Auth"])
auth_service = AuthService()


@router.post(
    "/login",
    summary="Login with email and password",
    description=(
        "Returns access token (30 min), refresh token (7 days), and is_password_changed flag. "
        "Frontend checks is_password_changed — if False, show 'please change your password' banner."
    ),
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    return auth_service.login(db, data.email, data.password)


@router.post(
    "/refresh",
    summary="Get a new access token using refresh token",
    description=(
        "Send the refresh token in Authorization header as Bearer. "
        "Returns a fresh access token. Refresh token itself is NOT rotated."
    ),
)
def refresh(
    current_user: User = Depends(get_refresh_token_user),
):
    return auth_service.refresh_access_token(current_user)


@router.get(
    "/me",
    summary="Get current logged-in user profile",
    description="Returns user details from the access token. Frontend calls this on page load.",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return auth_service.get_profile(current_user)


@router.post(
    "/change-password",
    summary="Change own password",
    description=(
        "Any role can call this. "
        "Sets is_password_changed = True after success — removes the banner on frontend."
    ),
)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return auth_service.change_password(
        db, current_user, data.old_password, data.new_password
    )
