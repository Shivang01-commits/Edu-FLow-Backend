import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.book_service import BookService, ClassChapterService
from src.services.ai_services.book_ingestion_services import BookIngestionService
from src.utils.jwt_handler import require_role
from src.models.books_schema import (
    AssignChapterRequest,
    OverridePPTRequest,
    OverrideQABankRequest,
    OverrideQuizRequest,
    OverrideSummaryRequest,
    ResetOverridesRequest,
)

book_service = BookService()
chapter_service = ClassChapterService()
ai_service = BookIngestionService()


router = APIRouter(prefix="/class-chapters", tags=["Class Chapters"])


@router.post(
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


@router.get(
    "/teacher/class/{class_id}",
    summary="List all chapters for a class [teacher, admin] — includes unpublished",
)
def list_chapters_for_teacher(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.list_for_teacher(db, class_id)


@router.get(
    "/{class_chapter_id}/content",
    summary="Get full chapter content [teacher, admin] — works for drafts too",
)
def get_chapter_content(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.get_resolved_content(db, class_chapter_id)


@router.get(
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


@router.get(
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


@router.patch(
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


@router.patch(
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


@router.patch(
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


@router.patch(
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


@router.post(
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
            status_code=422,
            detail=f"Invalid fields: {invalid}. Allowed: {allowed}",
        )
    return chapter_service.reset_overrides(db, class_chapter_id, data.fields)


@router.post(
    "/{class_chapter_id}/publish",
    summary="Publish chapter — students can now see it [teacher, admin]",
)
def publish_chapter(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.publish_chapter(db, class_chapter_id)


@router.post(
    "/{class_chapter_id}/unpublish",
    summary="Unpublish chapter — hides it from students [teacher, admin]",
)
def unpublish_chapter(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin", "teacher")),
):
    return chapter_service.unpublish_chapter(db, class_chapter_id)


@router.delete(
    "/{class_chapter_id}",
    summary="Remove a chapter from a class [admin, sudo_admin]",
)
def delete_class_chapter(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin", "admin")),
):
    return chapter_service.delete_class_chapter(db, class_chapter_id)
