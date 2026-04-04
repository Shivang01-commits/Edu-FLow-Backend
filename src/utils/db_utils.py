import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import User, UserRole, School, Class


async def get_user_or_404(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRole = None,
) -> User:
    query = select(User).where(User.user_id == user_id)
    if role:
        query = query.where(User.role == role)

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        role_label = role.value.replace("_", " ") if role else "User"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{role_label.capitalize()} not found",
        )
    return user


async def get_school_or_404(
    db: AsyncSession,
    school_id: uuid.UUID,
) -> School:
    result = await db.execute(select(School).where(School.school_id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )
    return school


async def get_class_or_404(
    db: AsyncSession,
    class_id: uuid.UUID,
) -> Class:
    result = await db.execute(select(Class).where(Class.class_id == class_id))
    class_ = result.scalar_one_or_none()
    if not class_:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )
    return class_


async def check_email_unique(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email {email} already exists",
        )
