import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
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
def register_teacher(
    data: RegisterTeacherRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.register_teacher(
        db=db,
        admin=current_user,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
    )


@router.get(
    "/teachers",
    summary="List all teachers in your school [admin only]",
)
def list_teachers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.list_teachers(db, current_user)


@router.post(
    "/teachers/{user_id}/deactivate",
    summary="Deactivate a teacher [admin only]",
)
def deactivate_teacher(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.deactivate_user(db, current_user, user_id)


@router.post(
    "/teachers/{user_id}/resend-password",
    summary="Resend password to teacher [admin only]",
)
def resend_teacher_password(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.resend_password(db, current_user, user_id)


@router.post(
    "/students/register",
    status_code=201,
    summary="Register a new student and enroll in a class [admin only]",
    description="Creates student account with random password, enrolls in class. Sends welcome email.",
)
def register_student(
    data: RegisterStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.register_student(
        db=db,
        admin=current_user,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        class_id=data.class_id,
    )


@router.get(
    "/students",
    summary="List all students in your school [admin only]",
)
def list_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.list_students(db, current_user)


@router.post(
    "/students/{user_id}/deactivate",
    summary="Deactivate a student [admin only]",
)
def deactivate_student(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.deactivate_user(db, current_user, user_id)


@router.post(
    "/students/{user_id}/resend-password",
    summary="Resend password to student [admin only]",
)
def resend_student_password(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.resend_password(db, current_user, user_id)


@router.post(
    "/classes",
    status_code=201,
    summary="Create a new class [admin only]",
)
def create_class(
    data: CreateClassRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.create_class(
        db=db,
        admin=current_user,
        class_name=data.class_name,
        grade_level=data.grade_level,
        section=data.section,
    )


@router.get(
    "/classes",
    summary="List all classes in your school [admin only]",
)
def list_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.list_classes(db, current_user)


@router.get(
    "/classes/{class_id}/students",
    summary="List all students in a class [admin only]",
)
def list_students_in_class(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.list_students_in_class(db, current_user, class_id)


@router.post(
    "/classes/{class_id}/assign-teacher",
    status_code=201,
    summary="Assign a teacher to a class [admin only]",
)
def assign_teacher_to_class(
    class_id: uuid.UUID,
    data: AssignTeacherRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return admin_service.assign_teacher_to_class(
        db=db,
        admin=current_user,
        class_id=class_id,
        teacher_id=data.teacher_id,
        subject=data.subject,
        is_classroom_teacher=data.is_classroom_teacher,
    )
