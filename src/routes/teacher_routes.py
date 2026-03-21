"""
teacher_router.py
-----------------
All endpoints for teacher role only.

GET /teacher/dashboard                          → landing page after login
GET /teacher/classes/{class_id}/chapters        → all chapters for a class
GET /teacher/classes/{class_id}/books           → global books to browse and assign
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.main import get_db
from src.db.models import User
from src.services.db_services.teacher_service import TeacherService
from src.utils.jwt_handler import require_role
from src.models.books_schema import EditChapterContentRequest,PublishContentRequest


router = APIRouter(prefix="/teacher", tags=["Teacher"])
teacher_service = TeacherService()


@router.get(
    "/dashboard",
    summary="Teacher dashboard",
    description=(
        "Landing page after login. "
        "Returns all assigned classes with subject, student count, "
        "and published vs unpublished chapter counts."
    ),
)
def teacher_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return teacher_service.get_dashboard(db, current_user)


@router.get(
    "/classes/{class_id}/chapters",
    summary="All chapters for a class",
    description=(
        "Returns both published and unpublished chapters for this class. "
        "Teacher sees everything. Students only see published ones."
    ),
)
def get_chapters_for_class(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return teacher_service.get_chapters_for_class(db, current_user, class_id)


@router.get(
    "/classes/{class_id}/books",
    summary="Browse global books available for a class",
    description=(
        "Returns global books filtered by class grade and teacher's subject. "
        "is_assigned = true means this chapter is already added to this class."
    ),
)
def get_available_books(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return teacher_service.get_available_books(db, current_user, class_id)


@router.get(
    "/book-names",
    summary="Get list of book names for a subject and grade [teacher only]",
    description=(
        "Returns distinct book names for given grade_level and subject. "
        "Used to populate dropdown in 'Generate Summary/Quiz/etc' form."
    ),
)
def get_book_names(
    grade_level: int,
    subject: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return teacher_service.get_book_names(db, grade_level, subject)

@router.post(
    "/class-chapters/edit",
    summary="Get chapter content for editing [teacher only]",
    description=(
        "When teacher clicks EDIT, this returns the content "
        "(from Book or ClassChapter if overridden) that can be edited. "
        "Also creates ClassChapter record if it doesn't exist."
    ),
)
def edit_chapter_content(
    data: EditChapterContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return teacher_service.edit_chapter_content(db, current_user, data)


@router.post(
    "/class-chapters/publish",
    summary="Publish modified content [teacher only]",
    description=(
        "Can be called with class_chapter_id (after EDIT) "
        "or with chapter metadata (direct publish without EDIT)"
    ),
)
def publish_chapter_content(
    data: PublishContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return teacher_service.publish_chapter_content(db, current_user, data)
