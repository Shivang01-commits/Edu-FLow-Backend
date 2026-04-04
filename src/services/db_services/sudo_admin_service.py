import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import User, UserRole, School, Enrollment, Class
from src.services.db_services.auth_service import hash_password
from src.services.email_service import send_admin_welcome_email
from src.services.db_services.admin_service import generate_random_password
from src.utils.db_utils import get_school_or_404, get_user_or_404


class SudoAdminService:
    async def register_school_with_admin(
        self,
        db: AsyncSession,
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

        # ✅ fixed — was missing .scalar_one_or_none()
        existing_result = await db.execute(
            select(School).where(School.admin_email == admin_email.lower().strip())
        )
        if existing_result.scalar_one_or_none():
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
        await db.flush()

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
        await db.commit()
        await db.refresh(school)
        await db.refresh(admin)

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
    # GET ALL ADMINS
    # -----------------------------------------------------------------------
    async def get_all_admins(self, db: AsyncSession, filter: str = "all") -> dict:

        # build query based on filter
        query = select(User).where(User.role == UserRole.admin)
        if filter == "active":
            query = query.where(User.is_active == True)
        elif filter == "revoked":
            query = query.where(User.is_active == False)
        query = query.order_by(User.created_at.desc())

        admins_result = await db.execute(query)
        admins = admins_result.scalars().all()

        # stats across ALL admins regardless of filter
        all_result = await db.execute(select(User).where(User.role == UserRole.admin))
        all_admins = all_result.scalars().all()
        total = len(all_admins)
        active_count = sum(1 for a in all_admins if a.is_active)
        revoked_count = total - active_count

        # fetch all schools for these admins in one query — no N+1
        school_ids = [a.school_id for a in admins if a.school_id]
        schools_result = await db.execute(
            select(School).where(School.school_id.in_(school_ids))
        )
        schools = schools_result.scalars().all()
        school_map = {s.school_id: s for s in schools}

        result = []
        for admin in admins:
            school = school_map.get(admin.school_id)
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

    # -----------------------------------------------------------------------
    # GET ADMIN BY ID
    # -----------------------------------------------------------------------
    async def get_admin_by_id(self, db: AsyncSession, admin_id: uuid.UUID) -> dict:
        admin = await get_user_or_404(db, admin_id, role=UserRole.admin)

        school_result = await db.execute(
            select(School).where(School.school_id == admin.school_id)
        )
        school = school_result.scalar_one_or_none()

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
    # GET SCHOOL WITH ADMIN DETAILS
    # -----------------------------------------------------------------------
    async def get_school_with_admin(
        self, db: AsyncSession, school_id: uuid.UUID
    ) -> dict:
        school = await get_school_or_404(db, school_id)

        admin_result = await db.execute(
            select(User).where(
                User.school_id == school_id,
                User.role == UserRole.admin,
                User.is_active == True,
            )
        )
        admin = admin_result.scalar_one_or_none()

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
    async def deactivate_school(self, db: AsyncSession, school_id: uuid.UUID) -> dict:
        school = await get_school_or_404(db, school_id)

        if not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School is already deactivated",
            )

        school.is_active = False

        # bulk update all users in this school — async way
        await db.execute(
            update(User)
            .where(
                User.school_id == school_id,
                User.role != UserRole.sudo_admin,
            )
            .values(is_active=False)
        )

        await db.commit()
        return {
            "message": f"School '{school.school_name}' deactivated. All associated users deactivated."
        }

    # -----------------------------------------------------------------------
    # LIST ALL SCHOOLS
    # -----------------------------------------------------------------------
    async def list_schools(self, db: AsyncSession) -> list[dict]:
        schools_result = await db.execute(select(School).order_by(School.school_name))
        schools = schools_result.scalars().all()

        # count enrolled students per school in one query
        counts_result = await db.execute(
            select(
                Enrollment.school_id,
                func.count(Enrollment.enrollment_id).label("count"),
            )
            .where(Enrollment.is_active == True)
            .group_by(Enrollment.school_id)
        )
        count_map = {str(row.school_id): row.count for row in counts_result.all()}

        return [
            {
                "school_id": str(s.school_id),
                "school_name": s.school_name,
                "city": s.city,
                "state": s.state,
                "board": s.board,
                "plan": s.plan,
                "is_active": s.is_active,
                "created_at": s.created_at,
                "stats": {
                    "students_enrolled": count_map.get(str(s.school_id), 0),
                },
            }
            for s in schools
        ]

    # -----------------------------------------------------------------------
    # GET SCHOOL BY ID
    # -----------------------------------------------------------------------
    async def get_school_by_id(self, db: AsyncSession, school_id: uuid.UUID) -> dict:
        school = await get_school_or_404(db, school_id)

        # all three counts in one round trip
        student_count_result = await db.execute(
            select(func.count(Enrollment.enrollment_id)).where(
                Enrollment.school_id == school_id,
                Enrollment.is_active == True,
            )
        )
        teacher_count_result = await db.execute(
            select(func.count(User.user_id)).where(
                User.school_id == school_id,
                User.role == UserRole.teacher,
                User.is_active == True,
            )
        )
        class_count_result = await db.execute(
            select(func.count(Class.class_id)).where(Class.school_id == school_id)
        )

        return {
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
            "stats": {
                "students_enrolled": student_count_result.scalar() or 0,
                "teachers": teacher_count_result.scalar() or 0,
                "classes": class_count_result.scalar() or 0,
            },
        }
