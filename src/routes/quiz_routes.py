import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.quiz_service import QuizService
from src.utils.jwt_handler import require_role
from src.models.quiz_schema import SubmitQuizRequest

router = APIRouter(prefix="/quiz", tags=["Quiz"])
quiz_service = QuizService()


@router.get(
    "/{class_chapter_id}/questions",
    summary="Get quiz questions [student]",
    description=(
        "Returns questions and options only. "
        "correct_answer and explanation are hidden until after submission. "
        "Returns 409 if student already attempted this quiz."
    ),
)
def get_quiz_questions(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return quiz_service.get_quiz_for_student(db, class_chapter_id, current_user)


@router.post(
    "/{class_chapter_id}/submit",
    status_code=201,
    summary="Submit quiz answers [student]",
    description=(
        "Auto-scored immediately. "
        "Returns full result with correct answers and explanations. "
        "One attempt per chapter — re-submission blocked with 409."
    ),
)
def submit_quiz(
    class_chapter_id: uuid.UUID,
    data: SubmitQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    # convert pydantic models to dicts for the service
    answers = [a.dict() for a in data.answers]
    return quiz_service.submit_quiz(db, class_chapter_id, current_user, answers)


@router.get(
    "/history",
    summary="All quiz attempts by this student [student]",
    description=(
        "Summary list — score, percentage, status per attempt. "
        "No full response JSONB here. "
        "Use GET /quiz/attempt/{id} for full result."
    ),
)
def get_quiz_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return quiz_service.get_student_history(db, current_user)


@router.get(
    "/attempt/{quiz_attempt_id}",
    summary="View full result of an attempt [student]",
    description=(
        "Returns full response JSONB with correct answers and explanations. "
        "Student can only view their own attempts."
    ),
)
def get_quiz_result(
    quiz_attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return quiz_service.get_result(db, quiz_attempt_id, current_user)


@router.get(
    "/chapter/{class_chapter_id}/attempts",
    summary="All student attempts for a chapter [teacher]",
    description=(
        "Returns class-level stats (total attempts, average score) "
        "and a row per student. No full response JSONB in list."
    ),
)
def get_chapter_attempts(
    class_chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return quiz_service.get_attempts_for_chapter(db, class_chapter_id, current_user)


@router.get(
    "/attempt/{quiz_attempt_id}/detail",
    summary="One student's full quiz response [teacher]",
    description=(
        "Full response JSONB — each question, student's answer, "
        "correct answer, is_correct flag, explanation."
    ),
)
def get_attempt_detail(
    quiz_attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    return quiz_service.get_attempt_detail_for_teacher(
        db, quiz_attempt_id, current_user
    )
