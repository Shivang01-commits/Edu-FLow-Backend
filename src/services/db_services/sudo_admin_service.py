import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models import User, UserRole, School
from src.services.db_services.auth_service import hash_password
from src.services.email_service import send_admin_welcome_email
from src.services.db_services.admin_service import generate_random_password


class SudoAdminService:
    # CREATE SCHOOL
    def create_school(
        self,
        db: Session,
        school_name: str,
        admin_email: str,
        school_address: Optional[str] = None,
        school_phone: Optional[str] = None,
    ) -> School:
        existing = (
            db.query(School)
            .filter(School.admin_email == admin_email.lower().strip())
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A school with admin email {admin_email} already exists",
            )

        school = School(
            school_name=school_name.strip(),
            school_address=school_address.strip() if school_address else None,
            school_phone=school_phone.strip() if school_phone else None,
            admin_email=admin_email.lower().strip(),
            is_active=True,
        )
        db.add(school)
        db.commit()
        db.refresh(school)
        return school

    # DEACTIVATE SCHOOL — soft deletes school + all its users
    def deactivate_school(self, db: Session, school_id: uuid.UUID) -> dict:
        school = self._get_school_or_404(db, school_id)

        if not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School is already deactivated",
            )

        school.is_active = False

        # deactivate all users of this school
        db.query(User).filter(
            User.school_id == school_id,
            User.role != UserRole.sudo_admin,
        ).update({"is_active": False})

        db.commit()
        return {
            "message": f"School '{school.school_name}' deactivated. All associated users deactivated."
        }

    # LIST ALL SCHOOLS
    def list_schools(self, db: Session) -> list[School]:
        return db.query(School).order_by(School.school_name).all()

    # GET SCHOOL BY ID
    def get_school_by_id(self, db: Session, school_id: uuid.UUID) -> School:
        return self._get_school_or_404(db, school_id)

    # CREATE ADMIN for a specific school
    # Only one active admin per school allowed at a time.
    def create_admin(
        self,
        db: Session,
        school_id: uuid.UUID,
        email: str,
        first_name: str,
        last_name: Optional[str],
        date_of_birth: date,
    ) -> dict:
        # check email not already used
        existing_email = (
            db.query(User).filter(User.email == email.lower().strip()).first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with email {email} already exists",
            )

        school = self._get_school_or_404(db, school_id)

        # enforce one active admin per school
        existing_admin = (
            db.query(User)
            .filter(
                User.school_id == school_id,
                User.role == UserRole.admin,
                User.is_active == True,
            )
            .first()
        )
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"School '{school.school_name}' already has an active admin "
                    f"({existing_admin.email}). "
                    f"Deactivate the existing admin first."
                ),
            )

        raw_password = generate_random_password()

        admin = User(
            school_id=school_id,
            email=email.lower().strip(),
            password_hash=hash_password(raw_password),
            first_name=first_name.strip(),
            last_name=last_name.strip() if last_name else None,
            date_of_birth=date_of_birth,
            role=UserRole.admin,
            is_active=True,
            is_password_changed=False,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        send_admin_welcome_email(
            to_email=email,
            first_name=first_name,
            school_name=school.school_name,
            password=raw_password,
        )

        return {
            "message": f"Admin created for '{school.school_name}'. Login details sent to their email.",
            "admin_id": str(admin.user_id),
            "email": admin.email,
            "school": school.school_name,
        }

    # Internal
    def _get_school_or_404(self, db: Session, school_id: uuid.UUID) -> School:
        school = db.query(School).filter(School.school_id == school_id).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
            )
        return school
