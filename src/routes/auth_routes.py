"""
NOTE: Registration is NOT here.
        Teachers and students are registered by admin via /admin/teachers/register
        and /admin/students/register. There is no self-registration.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.auth_schema import LoginRequest, ChangePasswordRequest
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.auth_service import AuthService
from src.utils.jwt_handler import get_current_user, get_refresh_token_user

router = APIRouter(prefix="/auth", tags=["Auth"])
auth_service = AuthService()


@router.post("/admin/login", summary="Admin login")
async def admin_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(
        db, data.email, data.password, required_role="admin"
    )


@router.post("/sudo-admin/login", summary="Sudo admin login")
async def sudo_admin_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(
        db, data.email, data.password, required_role="sudo_admin"
    )


@router.post("/teacher/login", summary="Teacher login")
async def teacher_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(
        db, data.email, data.password, required_role="teacher"
    )


@router.post("/student/login", summary="Student login")
async def student_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(
        db, data.email, data.password, required_role="student"
    )


@router.post(
    "/refresh",
    summary="Get a new access token using refresh token",
    description=(
        "Send the refresh token in Authorization header as Bearer. "
        "Returns a fresh access token. Refresh token itself is NOT rotated."
    ),
)
async def refresh(
    current_user: User = Depends(get_refresh_token_user),
):
    return auth_service.refresh_access_token(current_user)  # no await — no DB access


@router.get(
    "/me",
    summary="Get current logged-in user profile",
    description="Returns user details from the access token. Frontend calls this on page load.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return auth_service.get_profile(current_user)  # no await — no DB access


@router.post(
    "/change-password",
    summary="Change own password",
    description=(
        "Any role can call this. "
        "Sets is_password_changed = True after success — removes the banner on frontend."
    ),
)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await auth_service.change_password(
        db, current_user, data.old_password, data.new_password
    )
