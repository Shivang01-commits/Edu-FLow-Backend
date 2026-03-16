import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.db.models import User, Class, ClassTeacher, ClassChapter, Enrollment, Book


class TeacherService:
    # DASHBOARD — main landing page for teacher after login
    # Returns all assigned classes with stats
    def get_dashboard(self, db: Session, teacher: User) -> dict:
        assigned_classes = self._get_assigned_classes(db, teacher.user_id)

        if not assigned_classes:
            return {
                "teacher": self._teacher_profile(teacher),
                "total_classes": 0,
                "classes": [],
            }

        classes_data = []
        for ct in assigned_classes:
            class_ = ct.class_
            school = class_.school

            published_count = (
                db.query(ClassChapter)
                .filter(
                    ClassChapter.class_id == class_.class_id,
                    ClassChapter.teacher_id == teacher.user_id,
                    ClassChapter.published_date is not None,
                )
                .count()
            )

            total_count = (
                db.query(ClassChapter)
                .filter(
                    ClassChapter.class_id == class_.class_id,
                    ClassChapter.teacher_id == teacher.user_id,
                )
                .count()
            )

            student_count = (
                db.query(Enrollment)
                .filter(
                    Enrollment.class_id == class_.class_id,
                    Enrollment.is_active,
                )
                .count()
            )

            classes_data.append(
                {
                    "class_id": str(class_.class_id),
                    "class_name": class_.class_name,
                    "section": class_.section,
                    "grade_level": class_.grade_level,
                    "school_name": school.school_name,
                    "subject": ct.subject,
                    "is_classroom_teacher": ct.is_classroom_teacher,
                    "student_count": student_count,
                    "total_chapters": total_count,
                    "published_chapters": published_count,
                    "unpublished_chapters": total_count - published_count,
                }
            )

        return {
            "teacher": self._teacher_profile(teacher),
            "total_classes": len(classes_data),
            "classes": classes_data,
        }

    # CHAPTERS — all chapters for a class (published + unpublished)
    # Teacher sees everything — students only see published ones
    def get_chapters_for_class(
        self, db: Session, teacher: User, class_id: uuid.UUID
    ) -> dict:
        assignment = self._get_assignment_or_403(db, teacher.user_id, class_id)

        chapters = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == class_id,
                ClassChapter.teacher_id == teacher.user_id,
            )
            .order_by(ClassChapter.subject, ClassChapter.chapter_title)
            .all()
        )

        return {
            "class_id": str(class_id),
            "subject": assignment.subject,
            "chapters": [
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "chapter_title": ch.chapter_title,
                    "subject": ch.subject,
                    "is_published": ch.published_date is not None,
                    "published_date": ch.published_date,
                    "last_modified": ch.last_modified_date,
                    "overrides": {
                        "summary": ch.is_summary_overridden,
                        "qa_bank": ch.is_qa_bank_overridden,
                        "quiz": ch.is_quiz_overridden,
                        "ppt_structure": ch.is_ppt_overridden,
                    },
                }
                for ch in chapters
            ],
        }

    # AVAILABLE BOOKS — global books teacher can browse and assign to class
    # Filtered by class grade + teacher's subject
    # is_assigned = True means this book chapter is already added to the class
    def get_available_books(
        self, db: Session, teacher: User, class_id: uuid.UUID
    ) -> dict:
        assignment = self._get_assignment_or_403(db, teacher.user_id, class_id)

        class_ = db.query(Class).filter(Class.class_id == class_id).first()

        query = db.query(Book).filter(Book.class_grade == class_.grade_level)
        if assignment.subject:
            query = query.filter(Book.subject == assignment.subject.lower().strip())

        books = query.order_by(Book.book_name, Book.chapter_number).all()

        # collect book_ids already assigned to this class
        assigned_book_ids = {
            str(ch.book_id)
            for ch in db.query(ClassChapter)
            .filter(ClassChapter.class_id == class_id)
            .all()
            if ch.book_id
        }

        return {
            "class_id": str(class_id),
            "class_name": class_.class_name,
            "grade_level": class_.grade_level,
            "subject": assignment.subject,
            "total_books": len(books),
            "books": [
                {
                    "book_id": str(b.book_id),
                    "book_name": b.book_name,
                    "chapter_number": b.chapter_number,
                    "chapter_title": b.chapter_title,
                    "subject": b.subject,
                    "isbn": b.isbn,
                    "is_assigned": str(b.book_id) in assigned_book_ids,
                }
                for b in books
            ],
        }

    # Internal helpers
    def _get_assigned_classes(
        self, db: Session, teacher_id: uuid.UUID
    ) -> list[ClassTeacher]:
        return (
            db.query(ClassTeacher).filter(ClassTeacher.teacher_id == teacher_id).all()
        )

    def _get_assignment_or_403(
        self, db: Session, teacher_id: uuid.UUID, class_id: uuid.UUID
    ) -> ClassTeacher:
        assignment = (
            db.query(ClassTeacher)
            .filter(
                ClassTeacher.class_id == class_id,
                ClassTeacher.teacher_id == teacher_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this class",
            )
        return assignment

    def _teacher_profile(self, teacher: User) -> dict:
        return {
            "user_id": str(teacher.user_id),
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "email": teacher.email,
            "is_password_changed": teacher.is_password_changed,
        }
