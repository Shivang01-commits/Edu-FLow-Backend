import uuid
import json
import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.db.models import (
    User,
    ClassChapter,
    ClassTeacher,
    Enrollment,
    Quiz,
    Class,
    Book,
)
from src.models.quiz_schema import SubmitQuizRequest


class StudentService:
    async def get_dashboard(self, db: AsyncSession, student: User) -> dict:
        enrollment = await self._get_enrollment_or_404(db, student.user_id)

        # fetch class with school eagerly loaded
        class_result = await db.execute(
            select(Class)
            .where(Class.class_id == enrollment.class_id)
            .options(joinedload(Class.school))
        )
        class_ = class_result.scalar_one_or_none()
        school = class_.school

        # only published chapters visible to student
        chapters_result = await db.execute(
            select(ClassChapter)
            .where(
                ClassChapter.class_id == class_.class_id,
                ClassChapter.published_date.isnot(None),
            )
            .order_by(ClassChapter.subject)
        )
        published_chapters = chapters_result.scalars().all()

        # all teachers assigned to this class with teacher user eagerly loaded
        teachers_result = await db.execute(
            select(ClassTeacher)
            .where(ClassTeacher.class_id == class_.class_id)
            .options(joinedload(ClassTeacher.teacher))
        )
        class_teachers = teachers_result.scalars().all()

        # quiz attempts with class_chapter eagerly loaded
        attempts_result = await db.execute(
            select(Quiz)
            .where(Quiz.student_id == student.user_id)
            .options(joinedload(Quiz.class_chapter))
            .order_by(Quiz.submitted_date.desc())
        )
        quiz_attempts = attempts_result.scalars().all()

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
                "recent_attempts": [
                    {
                        "quiz_attempt_id": str(q.quiz_attempt_id),
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
    async def get_published_chapters(
        self, db: AsyncSession, student: User
    ) -> list[dict]:
        enrollment = await self._get_enrollment_or_404(db, student.user_id)

        result = await db.execute(
            select(ClassChapter)
            .where(
                ClassChapter.class_id == enrollment.class_id,
                ClassChapter.published_date.isnot(None),
            )
            .order_by(ClassChapter.subject)
        )
        chapters = result.scalars().all()

        return [
            {
                "class_chapter_id": str(ch.class_chapter_id),
                "subject": ch.subject,
                "published_date": ch.published_date,
            }
            for ch in chapters
        ]

    # QUIZ HISTORY
    async def get_quiz_history(self, db: AsyncSession, student: User) -> list[dict]:
        result = await db.execute(
            select(Quiz)
            .where(Quiz.student_id == student.user_id)
            .options(
                joinedload(Quiz.class_chapter)
            )  # needed for q.class_chapter.subject
            .order_by(Quiz.submitted_date.desc())
        )
        attempts = result.scalars().all()

        return [
            {
                "quiz_attempt_id": str(q.quiz_attempt_id),
                "subject": q.class_chapter.subject,
                "score": q.score,
                "total_questions": q.total_questions,
                "percentage": q.percentage,
                "status": q.status,
                "submitted_date": q.submitted_date,
            }
            for q in attempts
        ]

    # PRIVATE HELPER
    async def _get_enrollment_or_404(
        self, db: AsyncSession, student_id: uuid.UUID
    ) -> Enrollment:
        result = await db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.is_active == True,
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active enrollment found for this student",
            )
        return enrollment

    async def get_class_subjects(
        self, db: AsyncSession, student: User, class_id: uuid.UUID
    ) -> dict:
        # verify student is enrolled in this class
        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
        )
        if not enrollment_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        class_result = await db.execute(select(Class).where(Class.class_id == class_id))
        class_ = class_result.scalar_one_or_none()
        if not class_:
            raise HTTPException(status_code=404, detail="Class not found")

        # distinct subjects with published content
        subjects_result = await db.execute(
            select(ClassChapter.subject)
            .where(
                ClassChapter.class_id == class_id,
                ClassChapter.published_date.isnot(None),
            )
            .distinct()
            .order_by(ClassChapter.subject)
        )
        subjects = subjects_result.scalars().all()

        return {
            "class_id": str(class_id),
            "subjects": subjects,  # already a flat list of strings
        }

    async def get_published_content_for_subject(
        self,
        db: AsyncSession,
        student: User,
        class_id: uuid.UUID,
        subject: str,
        content_type: str,
    ) -> dict:
        # validate content_type
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        # verify enrollment
        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
        )
        if not enrollment_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        class_result = await db.execute(select(Class).where(Class.class_id == class_id))
        class_ = class_result.scalar_one_or_none()
        if not class_:
            raise HTTPException(status_code=404, detail="Class not found")

        override_flag = f"is_{content_type}_overridden"

        chapters_result = await db.execute(
            select(ClassChapter)
            .where(
                ClassChapter.class_id == class_id,
                ClassChapter.subject == subject.lower().strip(),
                ClassChapter.published_date.isnot(None),
                getattr(ClassChapter, override_flag) == True,
            )
            .order_by(ClassChapter.chapter_number)
        )
        chapters = chapters_result.scalars().all()

        return {
            "class_id": str(class_id),
            "subject": subject,
            "content_type": content_type,
            "total_published": len(chapters),
            "chapters": [
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "chapter_number": ch.chapter_number,
                    "published_date": ch.published_date,
                }
                for ch in chapters
            ],
        }

    async def get_student_chapter_content(
        self,
        db: AsyncSession,
        student: User,
        class_chapter_id: uuid.UUID,
        content_type: str,
    ) -> dict:
        # validate content_type
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        # get class chapter
        chapter_result = await db.execute(
            select(ClassChapter).where(
                ClassChapter.class_chapter_id == class_chapter_id
            )
        )
        class_chapter = chapter_result.scalar_one_or_none()
        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # verify enrollment
        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_chapter.class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
        )
        if not enrollment_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        # verify chapter is published
        if class_chapter.published_date is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This chapter has not been published yet",
            )

        # get content — custom if exists, else from Book
        content_field = f"custom_{content_type}"
        custom_content = getattr(class_chapter, content_field)

        if custom_content:
            content = custom_content
            is_customized = True
        else:
            book_result = await db.execute(
                select(Book).where(Book.book_id == class_chapter.book_id)
            )
            book = book_result.scalar_one_or_none()
            if not book:
                raise HTTPException(status_code=404, detail="Book not found")
            content = getattr(book, content_type)
            is_customized = False

        # get book info for context
        book_result = await db.execute(
            select(Book).where(Book.book_id == class_chapter.book_id)
        )
        book = book_result.scalar_one_or_none()

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

    async def submit_quiz(
        self,
        db: AsyncSession,
        student: User,
        class_chapter_id: uuid.UUID,
        data: SubmitQuizRequest,
    ) -> dict:
        # get class chapter
        chapter_result = await db.execute(
            select(ClassChapter).where(
                ClassChapter.class_chapter_id == class_chapter_id
            )
        )
        class_chapter = chapter_result.scalar_one_or_none()
        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # verify enrollment
        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_chapter.class_id,
                Enrollment.student_id == student.user_id,
                Enrollment.is_active == True,
            )
        )
        if not enrollment_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        # check if already submitted
        existing_result = await db.execute(
            select(Quiz).where(
                Quiz.class_chapter_id == class_chapter_id,
                Quiz.student_id == student.user_id,
                Quiz.status == "submitted",
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already submitted this quiz. Only one attempt is allowed.",
            )

        # get quiz content
        custom_quiz = class_chapter.custom_quiz
        if not custom_quiz:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz is not available for this chapter",
            )
        if isinstance(custom_quiz, str):
            custom_quiz = json.loads(custom_quiz)

        # calculate score
        score = 0
        questions = custom_quiz.get("quiz", {}).get("questions", [])
        total_questions = len(questions)

        for question in questions:
            question_id = str(question.get("id"))
            correct_answer = question.get("correct_answer")
            student_answer = data.student_answers.get(question_id)
            if student_answer and student_answer == correct_answer:
                score += 1

        percentage = (score / total_questions * 100) if total_questions > 0 else 0

        # check for pending attempt
        pending_result = await db.execute(
            select(Quiz).where(
                Quiz.class_chapter_id == class_chapter_id,
                Quiz.student_id == student.user_id,
                Quiz.status == "pending",
            )
        )
        pending_attempt = pending_result.scalar_one_or_none()

        if pending_attempt:
            pending_attempt.response = data.student_answers
            pending_attempt.score = score
            pending_attempt.total_questions = total_questions
            pending_attempt.percentage = percentage
            pending_attempt.status = "submitted"
            pending_attempt.submitted_date = datetime.datetime.now(
                datetime.timezone.utc
            )
            await db.commit()
            quiz_record = pending_attempt
        else:
            quiz_record = Quiz(
                school_id=class_chapter.school_id,
                class_chapter_id=class_chapter_id,
                student_id=student.user_id,
                response=data.student_answers,
                score=score,
                total_questions=total_questions,
                percentage=percentage,
                status="submitted",
                submitted_date=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(quiz_record)
            await db.commit()

        await db.refresh(quiz_record)

        return {
            "message": "Quiz submitted successfully",
            "quiz_attempt_id": str(quiz_record.quiz_attempt_id),
            "score": score,
            "total_questions": total_questions,
            "percentage": round(percentage, 2),
            "status": "submitted",
        }

    async def view_quiz_results(
        self, db: AsyncSession, student: User, quiz_attempt_id: uuid.UUID
    ) -> dict:
        # get quiz record
        quiz_result = await db.execute(
            select(Quiz).where(Quiz.quiz_attempt_id == quiz_attempt_id)
        )
        quiz_record = quiz_result.scalar_one_or_none()
        if not quiz_record:
            raise HTTPException(status_code=404, detail="Quiz attempt not found")

        # verify ownership
        if quiz_record.student_id != student.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this quiz result",
            )

        # get class chapter
        chapter_result = await db.execute(
            select(ClassChapter).where(
                ClassChapter.class_chapter_id == quiz_record.class_chapter_id
            )
        )
        class_chapter = chapter_result.scalar_one_or_none()
        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        custom_quiz = class_chapter.custom_quiz
        if isinstance(custom_quiz, str):
            custom_quiz = json.loads(custom_quiz)

        student_answers = quiz_record.response
        if isinstance(student_answers, str):
            student_answers = json.loads(student_answers)

        questions = custom_quiz.get("quiz", {}).get("questions", [])
        questions_breakdown = [
            {
                "id": question.get("id"),
                "question_text": question.get("question_text"),
                "options": question.get("options", {}),
                "student_answer": student_answers.get(str(question.get("id"))),
                "correct_answer": question.get("correct_answer"),
                "is_correct": student_answers.get(str(question.get("id")))
                == question.get("correct_answer")
                if student_answers.get(str(question.get("id")))
                else False,
                "explanation": question.get("explanation"),
            }
            for question in questions
        ]

        pass_fail = "PASS" if quiz_record.percentage >= 40 else "FAIL"

        return {
            "quiz_attempt_id": str(quiz_record.quiz_attempt_id),
            "score": quiz_record.score,
            "total_questions": quiz_record.total_questions,
            "percentage": quiz_record.percentage,
            "pass_fail": pass_fail,
            "submitted_date": quiz_record.submitted_date,
            "questions": questions_breakdown,
        }

    async def get_student_quiz_attempts(
        self,
        db: AsyncSession,
     student: User,
    ) -> list[dict]:

        result = await db.execute(
            select(Quiz)
            .where(
                Quiz.student_id == student.user_id,
                Quiz.status == "submitted",   # only attempted
            )
            .order_by(Quiz.submitted_date.desc())
        )

        quiz_attempts = result.scalars().all()

        return [
            {
            "quiz_attempt_id": str(quiz.quiz_attempt_id),
            "class_chapter_id": str(quiz.class_chapter_id),
            "score": quiz.score,
            "total_questions": quiz.total_questions,
            "percentage": round(quiz.percentage, 2),
            "submitted_date": quiz.submitted_date,
            "status": quiz.status,
            }
            for quiz in quiz_attempts
        ]