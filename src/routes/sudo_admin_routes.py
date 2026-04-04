import uuid
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_db
from src.db.models import User
from src.services.db_services.sudo_admin_service import SudoAdminService
from src.utils.cloudinary_utils import upload_school_document
from src.utils.jwt_handler import require_role

router = APIRouter(prefix="/sudo", tags=["Sudo Admin"])
sudo_admin_service = SudoAdminService()


# REGISTER SCHOOL + ADMIN — 3-step form


@router.post(
    "/schools/register",
    status_code=201,
    summary="Register school + create admin in one step [sudo_admin only]",
)
async def register_school(
    # Step 1 — School details
    school_name: str = Form(...),
    admin_email: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    board: str = Form(...),
    affiliation_number: str = Form(...),
    plan: str = Form(...),
    school_address: str = Form(""),
    school_phone: str = Form(""),
    # Step 1 — Document uploads
    registration_certificate: Optional[UploadFile] = File(None),
    noc_affiliation: Optional[UploadFile] = File(None),
    # Step 2 — Admin details
    admin_first_name: str = Form(...),
    admin_last_name: str = Form(""),
    phone_number: str = Form(""),
    admin_date_of_birth: str = Form(""),
    # Auth
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    reg_cert_url = None
    noc_url = None

    if registration_certificate and registration_certificate.filename:
        reg_cert_url = upload_school_document(
            file=registration_certificate,
            school_name=school_name,
            doc_type="registration_certificate",
        )

    if noc_affiliation and noc_affiliation.filename:
        noc_url = upload_school_document(
            file=noc_affiliation,
            school_name=school_name,
            doc_type="noc_affiliation",
        )

    dob = None
    if admin_date_of_birth:
        try:
            dob = date.fromisoformat(admin_date_of_birth)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="admin_date_of_birth must be in YYYY-MM-DD format e.g. 1990-01-15",
            )

    return await sudo_admin_service.register_school_with_admin(
        db=db,
        school_name=school_name,
        admin_email=admin_email,
        city=city,
        state=state,
        board=board,
        affiliation_number=affiliation_number,
        plan=plan,
        school_address=school_address or None,
        school_phone=school_phone or None,
        registration_certificate_url=reg_cert_url,
        noc_affiliation_url=noc_url,
        admin_first_name=admin_first_name,
        admin_last_name=admin_last_name or None,
        phone_number=phone_number or None,
        admin_date_of_birth=dob,
    )


# ADMIN MANAGEMENT PAGE


@router.get(
    "/admins",
    summary="Get all admins across all schools [sudo_admin only]",
    description=(
        "Returns stats (total, active, revoked) + list of all admins. "
        "Use filter query param to narrow results: all | active | revoked. "
        "Matches the Admin Management page in the UI."
    ),
)
async def get_all_admins(
    filter: str = Query("all", enum=["all", "active", "revoked"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await sudo_admin_service.get_all_admins(db, filter=filter)


# SCHOOL MANAGEMENT


@router.get(
    "/schools",
    summary="List all schools [sudo_admin only]",
)
async def list_schools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await sudo_admin_service.list_schools(db)


# get school + admin details route
@router.get(
    "/schools/{school_id}/details",
    summary="Get school + admin full details [sudo_admin only]",
    description="Returns complete school info + admin profile. admin is null if none exists.",
)
async def get_school_with_admin(
    school_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await sudo_admin_service.get_school_with_admin(db, school_id)


@router.get(
    "/schools/{school_id}",
    summary="Get school by ID [sudo_admin only]",
)
async def get_school(
    school_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await sudo_admin_service.get_school_by_id(db, school_id)


@router.get(
    "/admins/{admin_id}",
    summary="Get admin by ID [sudo_admin only]",
)
async def get_admin(
    admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await sudo_admin_service.get_admin_by_id(db, admin_id)


@router.post(
    "/schools/{school_id}/deactivate",
    summary="Deactivate a school and all its users [sudo_admin only]",
)
async def deactivate_school(
    school_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await sudo_admin_service.deactivate_school(db, school_id)
