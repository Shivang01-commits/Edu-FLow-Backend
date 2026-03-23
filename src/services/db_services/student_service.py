import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import datetime
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
import json


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

    def submit_quiz(
        self,
        db: Session,
        student: User,
        class_chapter_id: uuid.UUID,
        data: SubmitQuizRequest,
    ) -> dict:

        # Step 1: Verify student is enrolled in the class
        class_chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == class_chapter_id)
            .first()
        )

        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

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

        # Step 2: Check if student already attempted this quiz
        existing_attempt = (
            db.query(Quiz)
            .filter(
                Quiz.class_chapter_id == class_chapter_id,
                Quiz.student_id == student.user_id,
                Quiz.status == "submitted",
            )
            .first()
        )

        if existing_attempt:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already submitted this quiz. Only one attempt is allowed.",
            )

        # Step 3: Get the custom_quiz JSON from ClassChapter
        custom_quiz = class_chapter.custom_quiz

        if not custom_quiz:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz is not available for this chapter",
            )

        # If custom_quiz is stored as string, parse it
        if isinstance(custom_quiz, str):
            custom_quiz = json.loads(custom_quiz)

        # Step 4: Calculate score by comparing answers
        score = 0
        questions = custom_quiz.get("quiz", {}).get("questions", [])

        total_questions = len(questions)

        for question in questions:
            question_id = str(question.get("id"))
            correct_answer = question.get("correct_answer")
            student_answer = data.student_answers.get(question_id)

            # If student answered this question, check if correct
            if student_answer and student_answer == correct_answer:
                score += 1

        # Step 5: Calculate percentage and pass/fail
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        pass_fail = "PASS" if percentage >= 40 else "FAIL"

        # Step 6: Check if there's an existing pending attempt
        pending_attempt = (
            db.query(Quiz)
            .filter(
                Quiz.class_chapter_id == class_chapter_id,
                Quiz.student_id == student.user_id,
                Quiz.status == "pending",
            )
            .first()
        )

        # Step 7: Create or update Quiz record
        if pending_attempt:
            # Update existing pending attempt
            pending_attempt.response = data.student_answers
            pending_attempt.score = score
            pending_attempt.total_questions = total_questions
            pending_attempt.percentage = percentage
            pending_attempt.status = "submitted"
            pending_attempt.submitted_date = datetime.datetime.now()
            db.commit()
            quiz_record = pending_attempt
        else:
            # Create new Quiz record
            quiz_record = Quiz(
                school_id=class_chapter.school_id,
                class_chapter_id=class_chapter_id,
                student_id=student.user_id,
                response=data.student_answers,
                score=score,
                total_questions=total_questions,
                percentage=percentage,
                status="submitted",
                submitted_date=datetime.datetime.now(),
            )
            db.add(quiz_record)
            db.commit()

        db.refresh(quiz_record)

        return {
            "message": "Quiz submitted successfully",
            "quiz_attempt_id": str(quiz_record.quiz_attempt_id),
            "score": score,
            "total_questions": total_questions,
            "percentage": round(percentage, 2),
            "status": "submitted",
        }

    def view_quiz_results(
        self, db: Session, student: User, quiz_attempt_id: uuid.UUID
    ) -> dict:
        import json

        # Step 1: Get Quiz record
        quiz_record = (
            db.query(Quiz).filter(Quiz.quiz_attempt_id == quiz_attempt_id).first()
        )

        if not quiz_record:
            raise HTTPException(status_code=404, detail="Quiz attempt not found")

        # Step 2: Verify student owns this quiz attempt
        if quiz_record.student_id != student.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this quiz result",
            )

        # Step 3: Get ClassChapter to fetch custom_quiz JSON
        class_chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == quiz_record.class_chapter_id)
            .first()
        )

        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        custom_quiz = class_chapter.custom_quiz

        if isinstance(custom_quiz, str):
            custom_quiz = json.loads(custom_quiz)

        # Step 4: Get student's answers from response field
        student_answers = quiz_record.response

        if isinstance(student_answers, str):
            student_answers = json.loads(student_answers)

        # Step 5: Build detailed question breakdown (on-the-fly comparison)
        questions_breakdown = []

        questions = custom_quiz.get("quiz", {}).get("questions", [])

        for question in questions:
            question_id = str(question.get("id"))
            question_text = question.get("question_text")
            options = question.get("options", {})
            correct_answer = question.get("correct_answer")
            explanation = question.get("explanation")

            student_answer = student_answers.get(question_id)
            is_correct = student_answer == correct_answer if student_answer else False

            questions_breakdown.append(
                {
                    "id": question.get("id"),
                    "question_text": question_text,
                    "options": options,
                    "student_answer": student_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "explanation": explanation,
                }
            )

        # Step 6: Determine pass/fail
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
