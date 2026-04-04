import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.admin_service import AdminService
from src.utils.jwt_handler import require_role
from src.models.admin_schema import (
    CreateClassRequest,
    AssignTeacherRequest,
    RegisterStudentRequest,
    RegisterTeacherRequest,
)

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_service = AdminService()


@router.post(
    "/teachers/register",
    status_code=201,
    summary="Register a new teacher [admin only]",
    description="Creates teacher account with random password. Sends welcome email.",
)
async def register_teacher(
    data: RegisterTeacherRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.register_teacher(
        db=db,
        admin=current_user,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        designation=data.designation,
        join_date=data.join_date,
        salary=data.salary,
        phone_number=data.phone_number,
    )


@router.get(
    "/teachers",
    summary="List all teachers in your school [admin only]",
)
async def list_teachers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.list_teachers(db, current_user)


@router.post(
    "/teachers/{user_id}/deactivate",
    summary="Deactivate a teacher [admin only]",
)
async def deactivate_teacher(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.deactivate_user(db, current_user, user_id)


@router.post(
    "/teachers/{user_id}/resend-password",
    summary="Resend password to teacher [admin only]",
)
async def resend_teacher_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.resend_password(db, current_user, user_id)


@router.post(
    "/students/register",
    status_code=201,
    summary="Register a new student and enroll in a class [admin only]",
    description="Creates student account with random password, enrolls in class. Sends welcome email.",
)
async def register_student(
    data: RegisterStudentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.register_student(
        db=db,
        admin=current_user,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        class_grade=data.class_grade,
        section=data.section,
        admission_number=data.admission_number,
        parent_name=data.parent_name,
        parent_phone=data.parent_phone,
    )


@router.get(
    "/students",
    summary="List all students in your school [admin only]",
)
async def list_students(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.list_students(db, current_user)


@router.get(
    "/students/{student_id}",
    summary="Get single student details [admin only]",
    description=(
        "Returns full student profile including enrollment details. "
        "403 if student belongs to a different school."
    ),
)
async def get_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.get_student_by_id(db, current_user, student_id)


@router.get(
    "/teachers/{teacher_id}",
    summary="Get single teacher details [admin only]",
    description=(
        "Returns full teacher profile including all assigned classes and subjects. "
        "403 if teacher belongs to a different school."
    ),
)
async def get_teacher(
    teacher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.get_teacher_by_id(db, current_user, teacher_id)


@router.post(
    "/students/{user_id}/deactivate",
    summary="Deactivate a student [admin only]",
)
async def deactivate_student(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.deactivate_user(db, current_user, user_id)


@router.post(
    "/students/{user_id}/resend-password",
    summary="Resend password to student [admin only]",
)
async def resend_student_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.resend_password(db, current_user, user_id)


@router.post(
    "/classes",
    status_code=201,
    summary="Create a new class [admin only]",
)
async def create_class(
    data: CreateClassRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.create_class(
        db=db,
        admin=current_user,
        grade_level=data.grade_level,
        section=data.section,
    )


@router.get(
    "/classes",
    summary="List all classes in your school [admin only]",
)
async def list_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.list_classes(db, current_user)


@router.get(
    "/classes/{class_id}/students",
    summary="List all students in a class [admin only]",
)
async def list_students_in_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.list_students_in_class(db, current_user, class_id)


@router.post(
    "/classes/{class_id}/assign-teacher",
    status_code=201,
    summary="Assign a teacher to a class [admin only]",
)
async def assign_teacher_to_class(
    class_id: uuid.UUID,
    data: AssignTeacherRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.assign_teacher_to_class(
        db=db,
        admin=current_user,
        class_id=class_id,
        teacher_id=data.teacher_id,
        subject=data.subject,
        is_classroom_teacher=data.is_classroom_teacher,
    )


@router.get(
    "/classes/{class_id}",
    summary="Get class details [admin only]",
    description=(
        "Returns full class profile including enrollment details. "
        "403 if class belongs to a different school."
    ),
)
async def get_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.get_class_by_id(db, current_user, class_id)


@router.delete(
    "/classes/{class_id}",
    summary="Delete a class [admin only]",
    description="Cannot delete if students are actively enrolled.",
)
async def delete_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.delete_class(db, current_user, class_id)


@router.post(
    "/students/bulk-enroll",
    status_code=200,
    summary="Bulk enroll students from Excel/CSV file [admin only]",
    description=(
        "Upload Excel or CSV file with student data to enroll multiple students at once. "
        "Validates all rows first, then enrolls if no errors. "
        "Returns summary with enrolled count, skipped rows, and failed rows."
    ),
)
async def bulk_enroll_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await admin_service.bulk_enroll_students(db, current_user, file)
