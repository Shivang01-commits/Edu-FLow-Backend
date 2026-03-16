from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
