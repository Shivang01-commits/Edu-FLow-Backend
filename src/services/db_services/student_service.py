import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.db.models import (
    User,
    ClassChapter,
    ClassTeacher,
    Enrollment,
    Quiz,
    Class,
    Book,
)


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
            .order_by(ClassChapter.subject)
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
                # "class_name": class_.class_name,
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
                    # "chapter_title": ch.chapter_title,
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
                        # "chapter_title": q.class_chapter.chapter_title,
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
            .order_by(ClassChapter.subject)
            .all()
        )

        return [
            {
                "class_chapter_id": str(ch.class_chapter_id),
                # "chapter_title": ch.chapter_title,
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
                # "chapter_title": q.class_chapter.chapter_title,
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

    def get_class_subjects(
        self, db: Session, student: User, class_id: uuid.UUID
    ) -> dict:

        # Step 1: Verify student is enrolled in this class
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.class_id == class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
            .first()
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        # Step 2: Get class info
        class_ = db.query(Class).filter(Class.class_id == class_id).first()
        if not class_:
            raise HTTPException(status_code=404, detail="Class not found")

        # Step 3: Get all distinct subjects with published content in this class
        subjects = (
            db.query(ClassChapter.subject)
            .filter(
                ClassChapter.class_id == class_id,
                ClassChapter.published_date.isnot(None),
            )
            .distinct()
            .order_by(ClassChapter.subject)
            .all()
        )

        return {
            "class_id": str(class_id),
            # "class_name": class_.class_name,
            "subjects": [s[0] for s in subjects],
        }

    def get_published_content_for_subject(
        self,
        db: Session,
        student: User,
        class_id: uuid.UUID,
        subject: str,
        content_type: str,
    ) -> dict:

        # Step 1: Validate content_type
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        # Step 2: Verify student is enrolled in this class
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.class_id == class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
            .first()
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        # Step 3: Get class info
        class_ = db.query(Class).filter(Class.class_id == class_id).first()
        if not class_:
            raise HTTPException(status_code=404, detail="Class not found")

        # Step 4: Build the override flag column name
        override_flag = f"is_{content_type}_overridden"

        # Step 5: Query ClassChapter records where this content is published
        chapters = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == class_id,
                ClassChapter.subject == subject.lower().strip(),
                ClassChapter.published_date.isnot(None),
                getattr(ClassChapter, override_flag) == True,
            )
            .order_by(ClassChapter.chapter_number)
            .all()
        )

        # Step 6: Build response
        content_list = []
        for ch in chapters:
            content_list.append(
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "chapter_number": ch.chapter_number,
                    "published_date": ch.published_date,
                }
            )

        return {
            "class_id": str(class_id),
            # "class_name": class_.class_name,
            "subject": subject,
            "content_type": content_type,
            "total_published": len(content_list),
            "chapters": content_list,
        }

    def get_student_chapter_content(
        self, db: Session, student: User, class_chapter_id: uuid.UUID, content_type: str
    ) -> dict:

        # Step 1: Validate content_type
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        # Step 2: Get ClassChapter record
        class_chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == class_chapter_id)
            .first()
        )

        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Step 3: Verify student is enrolled in this class
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.class_id == class_chapter.class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
            .first()
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        # Step 4: Verify chapter is published
        if class_chapter.published_date is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This chapter has not been published yet",
            )

        # Step 5: Get the content (custom if exists, else from Book)
        content_field = f"custom_{content_type}"
        custom_content = getattr(class_chapter, content_field)

        if custom_content:
            # Teacher customized this content
            content = custom_content
            is_customized = True
        else:
            # Use global book content
            book = db.query(Book).filter(Book.book_id == class_chapter.book_id).first()
            if not book:
                raise HTTPException(status_code=404, detail="Book not found")

            content = getattr(book, content_type)
            is_customized = False

        # Step 6: Get book info for context
        book = db.query(Book).filter(Book.book_id == class_chapter.book_id).first()

        return {
            "class_chapter_id": str(class_chapter_id),
            "book_name": book.book_name if book else None,
            "chapter_number": class_chapter.chapter_number,
            "subject": class_chapter.subject,
            "content_type": content_type,
            "is_customized": is_customized,
            "published_date": class_chapter.published_date,
            content_type: content,
        }
