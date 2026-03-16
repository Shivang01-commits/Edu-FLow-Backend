"""
sudo_admin_router.py
--------------------
All endpoints only sudo_admin can access:

Schools:
  POST /sudo/schools/                  → create school
  GET  /sudo/schools/                  → list all schools
  GET  /sudo/schools/{id}              → get school by ID
  POST /sudo/schools/{id}/deactivate   → deactivate school + all users

Admin management:
  POST /sudo/admins/create             → create admin for a school
"""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.sudo_admin_service import SudoAdminService
from src.utils.jwt_handler import require_role
from src.models.sudo_admin_schema import CreateAdminRequest, CreateSchoolRequest

router = APIRouter(prefix="/sudo", tags=["Sudo Admin"])
sudo_admin_service = SudoAdminService()


@router.post(
    "/schools",
    status_code=201,
    summary="Create a new school",
)
def create_school(
    data: CreateSchoolRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return sudo_admin_service.create_school(
        db=db,
        school_name=data.school_name,
        admin_email=data.admin_email,
        school_address=data.school_address,
        school_phone=data.school_phone,
    )


@router.get(
    "/schools",
    summary="List all schools",
)
def list_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return sudo_admin_service.list_schools(db)


@router.get(
    "/schools/{school_id}",
    summary="Get a school by ID",
)
def get_school(
    school_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return sudo_admin_service.get_school_by_id(db, school_id)


@router.post(
    "/schools/{school_id}/deactivate",
    summary="Deactivate a school and all its users",
)
def deactivate_school(
    school_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return sudo_admin_service.deactivate_school(db, school_id)


@router.post(
    "/admins/create",
    status_code=201,
    summary="Create a school admin",
    description=(
        "Creates an admin account for a specific school. "
        "Only one active admin per school is allowed at a time. "
        "Admin receives a random password via welcome email."
    ),
)
def create_admin(
    data: CreateAdminRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return sudo_admin_service.create_admin(
        db=db,
        school_id=data.school_id,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
    )
