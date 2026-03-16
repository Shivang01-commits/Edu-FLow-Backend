import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.main import get_db
from src.db.models import User
from src.services.db_services.book_service import BookService, ClassChapterService
from src.utils.jwt_handler import get_current_user, require_role
from src.models.books_schema import (
    AssignChapterRequest,
    CreateBookRequest,
    OverridePPTRequest,
    OverrideQABankRequest,
    OverrideQuizRequest,
    OverrideSummaryRequest,
    ResetOverridesRequest,
    UpdateBookFieldsRequest,
)

book_service = BookService()
chapter_service = ClassChapterService()

books_router = APIRouter(prefix="/books", tags=["Global Books"])


@books_router.post(
    "/",
    status_code=201,
    summary="Store a new global book chapter [sudo_admin only]",
)
def create_book(
    data: CreateBookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return book_service.create_book(
        db=db,
        book_name=data.book_name,
        class_grade=data.class_grade,
        subject=data.subject,
        chapter_number=data.chapter_number,
        chapter_title=data.chapter_title,
        scraped_chapter=data.scraped_chapter,
        summary=data.summary,
        qa_bank=data.qa_bank,
        quiz=data.quiz,
        ppt_structure=data.ppt_structure,
        isbn=data.isbn,
    )


@books_router.get(
    "/",
    summary="List global books [all roles]",
)
def list_books(
    book_name: Optional[str] = None,
    class_grade: Optional[int] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.list_books(
        db, book_name=book_name, class_grade=class_grade, subject=subject
    )


@books_router.get(
    "/search",
    summary="Get a chapter by book_name + class_grade + subject + chapter_number [all roles]",
)
def get_book_by_metadata(
    book_name: str,
    class_grade: int,
    subject: str,
    chapter_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.get_by_metadata(
        db, book_name, class_grade, subject, chapter_number
    )


@books_router.get(
    "/isbn/{isbn}",
    summary="Get all chapters of a textbook by ISBN [all roles]",
)
def list_chapters_by_isbn(
    isbn: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.list_chapters_by_isbn(db, isbn)


@books_router.get(
    "/{book_id}",
    summary="Get a global book by ID [all roles]",
)
def get_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.get_by_id(db, book_id)


@books_router.patch(
    "/{book_id}",
    summary="Update specific fields of a global book [sudo_admin only]",
)
def update_book(
    book_id: uuid.UUID,
    data: UpdateBookFieldsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    if not any(
        [
            data.summary,
            data.qa_bank,
            data.quiz,
            data.ppt_structure,
            data.chapter_title,
            data.isbn,
        ]
    ):
        raise HTTPException(status_code=422, detail="No fields provided to update")

    return book_service.update_book_fields(
        db=db,
        book_id=book_id,
        summary=data.summary,
        qa_bank=data.qa_bank,
        quiz=data.quiz,
        ppt_structure=data.ppt_structure,
        chapter_title=data.chapter_title,
        isbn=data.isbn,
    )


@books_router.delete(
    "/{book_id}",
    summary="Delete a global book [sudo_admin only]",
)
def delete_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return book_service.delete_book(db, book_id)


chapters_router = APIRouter(prefix="/class-chapters", tags=["Class Chapters"])


@chapters_router.post(
    "/{class_id}/assign",
    status_code=201,
    summary="Assign a global book chapter to a class [admin, teacher]",
)
def assign_chapter(
    class_id: uuid.UUID,
    data: AssignChapterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    school_id = current_user.school_id

    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no associated school",
        )

    return chapter_service.assign_to_class(
        db=db,
        school_id=school_id,
        class_id=class_id,
        book_id=data.book_id,
        teacher_id=data.teacher_id,
        chapter_title=data.chapter_title,
        subject=data.subject,
    )


@chapters_router.get(
    "/teacher/class/{class_id}",
    summary="List all chapters for a class [teacher, admin] — includes unpublished",
)
def list_chapters_for_teacher(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.list_for_teacher(db, class_id)


@chapters_router.get(
    "/{class_chapter_id}/content",
    summary="Get full chapter content [teacher, admin] — works for drafts too",
)
def get_chapter_content(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.get_resolved_content(db, class_chapter_id)


@chapters_router.get(
    "/student/class/{class_id}",
    summary="List all published chapters for student's class [student only]",
    description="Returns 403 if student is not enrolled in this class.",
)
def list_published_for_student(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return chapter_service.list_published_for_student(
        db, class_id, current_user.user_id
    )


@chapters_router.get(
    "/{class_chapter_id}/student-view",
    summary="Get a published chapter [student only]",
    description="Returns 403 if not enrolled or chapter not published.",
)
def get_student_content(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return chapter_service.get_content_for_student(
        db, class_chapter_id, current_user.user_id
    )


@chapters_router.patch(
    "/{class_chapter_id}/override/summary",
    summary="Teacher overrides summary [teacher, admin]",
)
def override_summary(
    class_chapter_id: uuid.UUID,
    data: OverrideSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.override_summary(db, class_chapter_id, data.summary)


@chapters_router.patch(
    "/{class_chapter_id}/override/qa-bank",
    summary="Teacher overrides Q&A bank [teacher, admin]",
)
def override_qa_bank(
    class_chapter_id: uuid.UUID,
    data: OverrideQABankRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.override_qa_bank(db, class_chapter_id, data.qa_bank)


@chapters_router.patch(
    "/{class_chapter_id}/override/quiz",
    summary="Teacher overrides quiz [teacher, admin]",
)
def override_quiz(
    class_chapter_id: uuid.UUID,
    data: OverrideQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.override_quiz(db, class_chapter_id, data.quiz)


@chapters_router.patch(
    "/{class_chapter_id}/override/ppt-structure",
    summary="Teacher overrides PPT structure [teacher, admin]",
)
def override_ppt(
    class_chapter_id: uuid.UUID,
    data: OverridePPTRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.override_ppt_structure(
        db, class_chapter_id, data.ppt_structure
    )


@chapters_router.post(
    "/{class_chapter_id}/reset-overrides",
    summary="Reset overrides back to global content [teacher, admin]",
)
def reset_overrides(
    class_chapter_id: uuid.UUID,
    data: ResetOverridesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    allowed = {"summary", "qa_bank", "quiz", "ppt_structure"}
    invalid = set(data.fields) - allowed

    if invalid:
        raise HTTPException(
            status_code=422, detail=f"Invalid fields: {invalid}. Allowed: {allowed}"
        )

    return chapter_service.reset_overrides(db, class_chapter_id, data.fields)


@chapters_router.post(
    "/{class_chapter_id}/publish",
    summary="Publish chapter — students can now see it [teacher, admin]",
)
def publish_chapter(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.publish_chapter(db, class_chapter_id)


@chapters_router.post(
    "/{class_chapter_id}/unpublish",
    summary="Unpublish chapter — hides it from students [teacher, admin]",
)
def unpublish_chapter(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.unpublish_chapter(db, class_chapter_id)


@chapters_router.delete(
    "/{class_chapter_id}",
    summary="Remove a chapter from a class [admin, sudo_admin]",
)
def delete_class_chapter(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin")),
):
    return chapter_service.delete_class_chapter(db, class_chapter_id)


router = APIRouter()
router.include_router(books_router)
router.include_router(chapters_router)
