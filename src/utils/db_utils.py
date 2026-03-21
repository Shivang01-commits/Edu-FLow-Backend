import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.db.models import User, UserRole, School, Class


def get_user_or_404(
    db: Session,
    user_id: uuid.UUID,
    role: UserRole = None,
) -> User:
    query = db.query(User).filter(User.user_id == user_id)
    if role:
        query = query.filter(User.role == role)
    user = query.first()
    if not user:
        role_label = role.value.replace("_", " ") if role else "User"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{role_label.capitalize()} not found",
        )
    return user


def get_school_or_404(
    db: Session,
    school_id: uuid.UUID,
) -> School:
    school = db.query(School).filter(School.school_id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )
    return school


def get_class_or_404(
    db: Session,
    class_id: uuid.UUID,
) -> Class:
    class_ = db.query(Class).filter(Class.class_id == class_id).first()
    if not class_:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )
    return class_


def check_email_unique(db: Session, email: str) -> None:
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email {email} already exists",
        )
