import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models import Quiz, ClassChapter, Enrollment, User


class QuizService:
    # GET QUIZ QUESTIONS
    # Returns questions + options only.
    # correct_answer and explanation are NEVER sent before submission.
    def get_quiz_for_student(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        student: User,
    ) -> dict:
        chapter = self._get_published_chapter_or_403(
            db, class_chapter_id, student.user_id
        )
        quiz = self._get_quiz_content(chapter)

        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quiz available for this chapter",
            )

        existing = self._get_existing_attempt(db, class_chapter_id, student.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"You have already attempted this quiz. "
                    f"Score: {existing.score}/{existing.total_questions} "
                    f"({existing.percentage}%). "
                    f"Use GET /quiz/attempt/{existing.quiz_attempt_id} to view your result."
                ),
            )

        # strip correct_answer and explanation — never send before submission
        questions = [
            {
                "question_number": q["question_number"],
                "question_text": q.get("question_text") or q.get("question", ""),
                "options": q["options"],
            }
            for q in quiz.get("questions", [])
        ]

        return {
            "class_chapter_id": str(class_chapter_id),
            "chapter_title": chapter.chapter_title,
            "subject": chapter.subject,
            "quiz_title": quiz.get("quiz_title", "Chapter Quiz"),
            "total_questions": len(questions),
            "total_marks": quiz.get("total_marks", len(questions)),
            "questions": questions,
        }

    # SUBMIT QUIZ
    # Auto-scores, builds response JSONB, sets submitted_date, status → "submitted"
    def submit_quiz(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        student: User,
        answers: list[dict],
    ) -> dict:
        chapter = self._get_published_chapter_or_403(
            db, class_chapter_id, student.user_id
        )
        quiz = self._get_quiz_content(chapter)

        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quiz available for this chapter",
            )

        existing = self._get_existing_attempt(db, class_chapter_id, student.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"You have already submitted this quiz. "
                    f"Score: {existing.score}/{existing.total_questions} "
                    f"({existing.percentage}%)"
                ),
            )

        if not answers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No answers provided",
            )

        questions = quiz.get("questions", [])
        total_questions = len(questions)

        answer_map = {
            a["question_number"]: a.get("selected_option", "").upper().strip()
            for a in answers
        }

        # auto-score + build response JSONB
        response = []
        score = 0

        for q in questions:
            qnum = q["question_number"]
            correct_answer = q.get("correct_answer", "").upper().strip()
            selected = answer_map.get(qnum)
            is_correct = (selected == correct_answer) if selected else False

            if is_correct:
                score += 1

            response.append(
                {
                    "question_number": qnum,
                    "question_text": q.get("question_text") or q.get("question", ""),
                    "options": q.get("options", {}),
                    "selected_option": selected,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "explanation": q.get("explanation", ""),
                }
            )

        percentage = (
            round((score / total_questions) * 100, 2) if total_questions else 0.0
        )

        quiz_attempt = Quiz(
            school_id=student.school_id,
            class_chapter_id=class_chapter_id,
            student_id=student.user_id,
            score=score,
            total_questions=total_questions,
            percentage=percentage,
            response=response,
            submitted_date=datetime.now(timezone.utc),
            status="submitted",
        )
        db.add(quiz_attempt)
        db.commit()
        db.refresh(quiz_attempt)

        return {
            "quiz_attempt_id": str(quiz_attempt.quiz_attempt_id),
            "chapter_title": chapter.chapter_title,
            "subject": chapter.subject,
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "status": "submitted",
            "submitted_date": quiz_attempt.submitted_date,
            "response": response,
        }

    # GET RESULT — student views their own attempt
    # correct_answer and explanation visible here
    def get_result(
        self,
        db: Session,
        quiz_attempt_id: uuid.UUID,
        student: User,
    ) -> dict:
        attempt = self._get_attempt_or_404(db, quiz_attempt_id)

        if attempt.student_id != student.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own quiz results",
            )

        chapter = attempt.class_chapter

        return {
            "quiz_attempt_id": str(attempt.quiz_attempt_id),
            "chapter_title": chapter.chapter_title,
            "subject": chapter.subject,
            "score": attempt.score,
            "total_questions": attempt.total_questions,
            "percentage": attempt.percentage,
            "status": attempt.status,
            "submitted_date": attempt.submitted_date,
            "response": attempt.response,
        }

    # GET STUDENT HISTORY — summary list, no full response JSONB
    def get_student_history(
        self,
        db: Session,
        student: User,
    ) -> list[dict]:
        attempts = (
            db.query(Quiz)
            .filter(Quiz.student_id == student.user_id)
            .order_by(Quiz.submitted_date.desc())
            .all()
        )

        return [
            {
                "quiz_attempt_id": str(a.quiz_attempt_id),
                "chapter_title": a.class_chapter.chapter_title,
                "subject": a.class_chapter.subject,
                "score": a.score,
                "total_questions": a.total_questions,
                "percentage": a.percentage,
                "status": a.status,
                "submitted_date": a.submitted_date,
            }
            for a in attempts
        ]

    # TEACHER — all attempts for a chapter they own
    def get_attempts_for_chapter(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        teacher: User,
    ) -> dict:
        chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == class_chapter_id)
            .first()
        )
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        if chapter.teacher_id != teacher.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the teacher of this chapter",
            )

        attempts = (
            db.query(Quiz)
            .filter(Quiz.class_chapter_id == class_chapter_id)
            .order_by(Quiz.submitted_date.desc())
            .all()
        )

        total_attempts = len(attempts)
        avg_percentage = (
            round(sum(a.percentage for a in attempts) / total_attempts, 2)
            if total_attempts
            else 0.0
        )

        return {
            "class_chapter_id": str(class_chapter_id),
            "chapter_title": chapter.chapter_title,
            "subject": chapter.subject,
            "total_attempts": total_attempts,
            "average_score": avg_percentage,
            "attempts": [
                {
                    "quiz_attempt_id": str(a.quiz_attempt_id),
                    "student_id": str(a.student_id),
                    "student_name": f"{a.student.first_name} {a.student.last_name or ''}".strip(),
                    "score": a.score,
                    "total_questions": a.total_questions,
                    "percentage": a.percentage,
                    "status": a.status,
                    "submitted_date": a.submitted_date,
                }
                for a in attempts
            ],
        }

    # TEACHER — one student's full response detail
    def get_attempt_detail_for_teacher(
        self,
        db: Session,
        quiz_attempt_id: uuid.UUID,
        teacher: User,
    ) -> dict:
        attempt = self._get_attempt_or_404(db, quiz_attempt_id)
        chapter = attempt.class_chapter

        if chapter.teacher_id != teacher.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the teacher of this chapter",
            )

        return {
            "quiz_attempt_id": str(attempt.quiz_attempt_id),
            "student_name": f"{attempt.student.first_name} {attempt.student.last_name or ''}".strip(),
            "student_email": attempt.student.email,
            "chapter_title": chapter.chapter_title,
            "subject": chapter.subject,
            "score": attempt.score,
            "total_questions": attempt.total_questions,
            "percentage": attempt.percentage,
            "status": attempt.status,
            "submitted_date": attempt.submitted_date,
            "response": attempt.response,
        }

    # Internal helpers

    def _get_published_chapter_or_403(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> ClassChapter:
        chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == class_chapter_id)
            .first()
        )
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        if not chapter.published_date:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This chapter has not been published yet",
            )

        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.class_id == chapter.class_id,
                Enrollment.is_active == True,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        return chapter

    def _get_quiz_content(self, chapter: ClassChapter) -> Optional[dict]:
        """
        Returns teacher's custom quiz if overridden,
        else falls back to global book quiz.
        Mirrors same resolution logic as book_service.get_resolved_content.
        """
        if chapter.is_quiz_overridden and chapter.custom_quiz:
            return chapter.custom_quiz
        if chapter.book and chapter.book.quiz:
            return chapter.book.quiz
        return None

    def _get_existing_attempt(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> Optional[Quiz]:
        return (
            db.query(Quiz)
            .filter(
                Quiz.class_chapter_id == class_chapter_id,
                Quiz.student_id == student_id,
            )
            .first()
        )

    def _get_attempt_or_404(self, db: Session, quiz_attempt_id: uuid.UUID) -> Quiz:
        attempt = db.query(Quiz).filter(Quiz.quiz_attempt_id == quiz_attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Quiz attempt not found")
        return attempt
