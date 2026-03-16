import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.db.models import User, ClassChapter, ClassTeacher, Enrollment, Quiz


class StudentService:
    def get_dashboard(self, db: Session, student: User) -> dict:
        enrollment = self._get_enrollment_or_404(db, student.user_id)
        class_ = enrollment.class_
        school = class_.school

        # only published chapters visible to student
        published_chapters = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == class_.class_id,
                ClassChapter.published_date.isnot(None),
            )
            .order_by(ClassChapter.subject, ClassChapter.chapter_title)
            .all()
        )

        # all teachers assigned to this class
        class_teachers = (
            db.query(ClassTeacher)
            .filter(ClassTeacher.class_id == class_.class_id)
            .all()
        )

        # quiz attempts by this student — most recent first
        quiz_attempts = (
            db.query(Quiz)
            .filter(Quiz.student_id == student.user_id)
            .order_by(Quiz.submitted_date.desc())
            .all()
        )

        return {
            "student": {
                "user_id": str(student.user_id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.email,
                "is_password_changed": student.is_password_changed,
            },
            "class": {
                "class_id": str(class_.class_id),
                "class_name": class_.class_name,
                "section": class_.section,
                "grade_level": class_.grade_level,
                "school_name": school.school_name,
                "enrolled_on": enrollment.enrollment_date,
            },
            "teachers": [
                {
                    "teacher_id": str(ct.teacher.user_id),
                    "first_name": ct.teacher.first_name,
                    "last_name": ct.teacher.last_name,
                    "subject": ct.subject,
                    "is_classroom_teacher": ct.is_classroom_teacher,
                }
                for ct in class_teachers
            ],
            "published_chapters": [
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "chapter_title": ch.chapter_title,
                    "subject": ch.subject,
                    "published_date": ch.published_date,
                }
                for ch in published_chapters
            ],
            "total_published_chapters": len(published_chapters),
            "quiz_summary": {
                "total_attempts": len(quiz_attempts),
                "average_score": (
                    round(
                        sum(q.percentage for q in quiz_attempts) / len(quiz_attempts), 2
                    )
                    if quiz_attempts
                    else 0.0
                ),
                # last 5 quiz attempts shown on dashboard
                "recent_attempts": [
                    {
                        "quiz_attempt_id": str(q.quiz_attempt_id),
                        "chapter_title": q.class_chapter.chapter_title,
                        "subject": q.class_chapter.subject,
                        "score": q.score,
                        "total_questions": q.total_questions,
                        "percentage": q.percentage,
                        "status": q.status,
                        "submitted_date": q.submitted_date,
                    }
                    for q in quiz_attempts[:5]
                ],
            },
        }

    # PUBLISHED CHAPTERS — full list for student's class
    def get_published_chapters(self, db: Session, student: User) -> list[dict]:
        enrollment = self._get_enrollment_or_404(db, student.user_id)

        chapters = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == enrollment.class_id,
                ClassChapter.published_date.isnot(None),
            )
            .order_by(ClassChapter.subject, ClassChapter.chapter_title)
            .all()
        )

        return [
            {
                "class_chapter_id": str(ch.class_chapter_id),
                "chapter_title": ch.chapter_title,
                "subject": ch.subject,
                "published_date": ch.published_date,
            }
            for ch in chapters
        ]

    # QUIZ HISTORY — complete history of all attempts, summary only
    def get_quiz_history(self, db: Session, student: User) -> list[dict]:
        attempts = (
            db.query(Quiz)
            .filter(Quiz.student_id == student.user_id)
            .order_by(Quiz.submitted_date.desc())
            .all()
        )

        return [
            {
                "quiz_attempt_id": str(q.quiz_attempt_id),
                "chapter_title": q.class_chapter.chapter_title,
                "subject": q.class_chapter.subject,
                "score": q.score,
                "total_questions": q.total_questions,
                "percentage": q.percentage,
                "status": q.status,
                "submitted_date": q.submitted_date,
            }
            for q in attempts
        ]

    def _get_enrollment_or_404(self, db: Session, student_id: uuid.UUID) -> Enrollment:
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.is_active,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active enrollment found for this student",
            )
        return enrollment
