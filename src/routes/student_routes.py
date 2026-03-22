from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.student_service import StudentService
from src.utils.jwt_handler import require_role

router = APIRouter(prefix="/student", tags=["Student"])
student_service = StudentService()


@router.get(
    "/dashboard",
    summary="Student dashboard [student only]",
    description=(
        "Landing page after login. Returns: "
        "enrolled class details, list of teachers with subjects, "
        "all published chapters, last 5 quiz attempts with average score."
    ),
)
def student_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return student_service.get_dashboard(db, current_user)


@router.get(
    "/chapters",
    summary="All published chapters for student's class [student only]",
    description=(
        "Returns only published chapters. "
        "Unpublished chapters are completely invisible. "
        "Use GET /class-chapters/{id}/student-view to read full content of a chapter."
    ),
)
def get_published_chapters(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return student_service.get_published_chapters(db, current_user)


@router.get(
    "/quiz-history",
    summary="Quiz attempt history [student only]",
    description=(
        "Summary list of all quiz attempts — score, percentage, status. "
        "Does NOT include full response JSONB. "
        "Use GET /quiz/attempt/{id} for full result with correct answers."
    ),
)
def get_quiz_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return student_service.get_quiz_history(db, current_user)


@router.get(
    "/classes/{class_id}/subjects",
    summary="Get list of subjects for a class [student only]",
    description=(
        "Returns all subjects taught in this class. "
        "Used to populate subject filter dropdown."
    ),
)
def get_class_subjects(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return student_service.get_class_subjects(db, current_user, class_id)


@router.get(
    "/classes/{class_id}/published-content",
    summary="Get published content list by subject and type [student only]",
    description=(
        "Returns list of chapters with published summaries, quizzes, qa_banks, or ppt_structures "
        "for a specific subject in the student's class."
    ),
)
def get_published_content_for_subject(
    class_id: uuid.UUID,
    subject: str,
    content_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return student_service.get_published_content_for_subject(
        db, current_user, class_id, subject, content_type
    )

@router.get(
    "/class-chapters/{class_chapter_id}/content",
    summary="Get published content (summary/quiz/etc) [student only]",
    description=(
        "Returns the actual content (summary, quiz, qa_bank, or ppt_structure) "
        "for a published chapter. Student must be enrolled in the class."
    ),
)
def get_student_chapter_content(
    class_chapter_id: uuid.UUID,
    content_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return student_service.get_student_chapter_content(
        db, current_user, class_chapter_id, content_type
    )