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
    def register_school_with_admin(
        self,
        db: Session,
        school_name: str,
        admin_email: str,
        city: str,
        state: str,
        board: str,
        affiliation_number: str,
        plan: str,
        school_address: Optional[str] = None,
        school_phone: Optional[str] = None,
        registration_certificate_url: Optional[str] = None,
        noc_affiliation_url: Optional[str] = None,
        admin_first_name: str = "",
        admin_last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        admin_date_of_birth: Optional[date] = None,
    ) -> dict:

        existing_school = (
            db.query(School)
            .filter(School.admin_email == admin_email.lower().strip())
            .first()
        )
        if existing_school:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A school with admin email {admin_email} already exists",
            )

        school = School(
            school_name=school_name.strip(),
            school_address=school_address.strip() if school_address else None,
            city=city.strip(),
            state=state.strip(),
            board=board.strip(),
            affiliation_number=affiliation_number.strip(),
            school_phone=school_phone.strip() if school_phone else None,
            admin_email=admin_email.lower().strip(),
            registration_certificate_url=registration_certificate_url,
            noc_affiliation_url=noc_affiliation_url,
            plan=plan,
            is_active=True,
        )
        db.add(school)
        db.flush()

        raw_password = generate_random_password()

        admin = User(
            school_id=school.school_id,
            email=admin_email.lower().strip(),
            password_hash=hash_password(raw_password),
            first_name=admin_first_name.strip(),
            last_name=admin_last_name.strip() if admin_last_name else None,
            date_of_birth=admin_date_of_birth,
            phone_number=phone_number,
            role=UserRole.admin,
            is_active=True,
            is_password_changed=False,
        )
        db.add(admin)
        db.commit()
        db.refresh(school)
        db.refresh(admin)

        send_admin_welcome_email(
            to_email=admin_email,
            first_name=admin_first_name,
            school_name=school.school_name,
            password=raw_password,
        )

        return {
            "message": (
                f"School '{school.school_name}' registered and admin created successfully. "
                f"Login credentials sent to {admin_email}."
            ),
            "school": {
                "school_id": str(school.school_id),
                "school_name": school.school_name,
                "city": school.city,
                "state": school.state,
                "board": school.board,
                "affiliation_number": school.affiliation_number,
                "admin_email": school.admin_email,
                "plan": school.plan,
                "registration_certificate_url": school.registration_certificate_url,
                "noc_affiliation_url": school.noc_affiliation_url,
                "is_active": school.is_active,
            },
            "admin": {
                "admin_id": str(admin.user_id),
                "email": admin.email,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "phone_number": admin.phone_number,
            },
        }

    # -----------------------------------------------------------------------
    # GET ALL ADMINS — for Admin Management page
    # Returns stats (total, active, revoked) + list of all admins
    # filter: "all" | "active" | "revoked"
    # -----------------------------------------------------------------------
    def get_all_admins(self, db: Session, filter: str = "all") -> dict:
        query = db.query(User).filter(User.role == UserRole.admin)

        if filter == "active":
            query = query.filter(User.is_active)
        elif filter == "revoked":
            query = query.filter(not User.is_active)

        admins = query.order_by(User.created_at.desc()).all()

        # stats always calculated across ALL admins regardless of filter
        all_admins = db.query(User).filter(User.role == UserRole.admin).all()
        total = len(all_admins)
        active_count = sum(1 for a in all_admins if a.is_active)
        revoked_count = total - active_count

        result = []
        for admin in admins:
            school = (
                db.query(School).filter(School.school_id == admin.school_id).first()
            )
            result.append(
                {
                    "admin_id": str(admin.user_id),
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "email": admin.email,
                    "phone_number": admin.phone_number,
                    "is_active": admin.is_active,
                    "is_password_changed": admin.is_password_changed,
                    "created_at": admin.created_at,
                    "school": {
                        "school_id": str(school.school_id),
                        "school_name": school.school_name,
                        "city": school.city,
                        "state": school.state,
                        "plan": school.plan,
                        "is_active": school.is_active,
                    }
                    if school
                    else None,
                }
            )

        return {
            "stats": {
                "total_admins": total,
                "active": active_count,
                "revoked": revoked_count,
            },
            "count": len(result),
            "admins": result,
        }

    def get_admin_by_id(self, db: Session, admin_id: uuid.UUID) -> dict:
        admin = self._get_user_or_404(db, admin_id, role=UserRole.admin)
        school = db.query(School).filter(School.school_id == admin.school_id).first()

        return {
            "admin_id": str(admin.user_id),
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "email": admin.email,
            "phone_number": admin.phone_number,
            "date_of_birth": admin.date_of_birth,
            "is_active": admin.is_active,
            "is_password_changed": admin.is_password_changed,
            "created_at": admin.created_at,
            "school": {
                "school_id": str(school.school_id),
                "school_name": school.school_name,
                "city": school.city,
                "state": school.state,
                "plan": school.plan,
                "board": school.board,
                "is_active": school.is_active,
            }
            if school
            else None,
        }

    # -----------------------------------------------------------------------
    # GET SCHOOL WITH ADMIN DETAILS — for individual school view
    # -----------------------------------------------------------------------
    def get_school_with_admin(self, db: Session, school_id: uuid.UUID) -> dict:
        school = self._get_school_or_404(db, school_id)

        admin = (
            db.query(User)
            .filter(
                User.school_id == school_id,
                User.role == UserRole.admin,
                User.is_active,
            )
            .first()
        )

        return {
            "school": {
                "school_id": str(school.school_id),
                "school_name": school.school_name,
                "school_address": school.school_address,
                "city": school.city,
                "state": school.state,
                "board": school.board,
                "affiliation_number": school.affiliation_number,
                "school_phone": school.school_phone,
                "admin_email": school.admin_email,
                "plan": school.plan,
                "registration_certificate_url": school.registration_certificate_url,
                "noc_affiliation_url": school.noc_affiliation_url,
                "is_active": school.is_active,
                "created_at": school.created_at,
            },
            "admin": {
                "admin_id": str(admin.user_id),
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email,
                "phone_number": admin.phone_number,
                "date_of_birth": admin.date_of_birth,
                "is_active": admin.is_active,
                "is_password_changed": admin.is_password_changed,
                "created_at": admin.created_at,
            }
            if admin
            else None,
        }

    # -----------------------------------------------------------------------
    # DEACTIVATE SCHOOL
    # -----------------------------------------------------------------------
    def deactivate_school(self, db: Session, school_id: uuid.UUID) -> dict:
        school = self._get_school_or_404(db, school_id)

        if not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School is already deactivated",
            )

        school.is_active = False

        db.query(User).filter(
            User.school_id == school_id,
            User.role != UserRole.sudo_admin,
        ).update({"is_active": False})

        db.commit()
        return {
            "message": f"School '{school.school_name}' deactivated. All associated users deactivated."
        }

    # -----------------------------------------------------------------------
    # LIST ALL SCHOOLS
    # -----------------------------------------------------------------------
    def list_schools(self, db: Session) -> list[School]:
        return db.query(School).order_by(School.school_name).all()

    # -----------------------------------------------------------------------
    # GET SCHOOL BY ID
    # -----------------------------------------------------------------------
    def get_school_by_id(self, db: Session, school_id: uuid.UUID) -> School:
        return self._get_school_or_404(db, school_id)

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------
    def _get_school_or_404(self, db: Session, school_id: uuid.UUID) -> School:
        school = db.query(School).filter(School.school_id == school_id).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
            )
        return school

    def _get_user_or_404(
        self,
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
