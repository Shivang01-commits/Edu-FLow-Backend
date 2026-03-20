import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.db.models import Book, ClassChapter, Enrollment


class BookService:
    def create_book(
        self,
        db: Session,
        book_name: str,
        class_grade: int,
        subject: str,
        board: str,
        chapter_number: int,
        chapter_title: str,
        scraped_chapter: str,
        summary: dict,
        qa_bank: dict,
        quiz: dict,
        ppt_structure: dict,
        isbn: Optional[str] = None,
    ) -> Book:
        existing = self._find(db, book_name, class_grade, subject, chapter_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Book already exists for "
                    f"{book_name} / Class {class_grade} / {subject} / Chapter {chapter_number}."
                ),
            )

        book = Book(
            book_name=book_name.strip(),
            class_grade=class_grade,
            subject=subject.lower().strip(),
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            isbn=isbn,
            board=board,
            scraped_chapter=scraped_chapter,
            summary=summary,
            qa_bank=qa_bank,
            quiz=quiz,
            ppt_structure=ppt_structure,
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return book

    # READ — by ID
    def get_by_id(self, db: Session, book_id: uuid.UUID) -> Book:
        book = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
        return book

    # READ — by metadata
    def get_by_metadata(
        self,
        db: Session,
        book_name: str,
        class_grade: int,
        subject: str,
        chapter_number: int,
    ) -> Book:
        book = self._find(db, book_name, class_grade, subject, chapter_number)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
        return book

    # READ — list with filters
    def list_books(
        self,
        db: Session,
        book_name: Optional[str] = None,
        class_grade: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> list[Book]:
        query = db.query(Book)
        if book_name:
            query = query.filter(Book.book_name == book_name.strip())
        if class_grade is not None:
            query = query.filter(Book.class_grade == class_grade)
        if subject:
            query = query.filter(Book.subject == subject.lower().strip())
        return query.order_by(
            Book.book_name, Book.class_grade, Book.subject, Book.chapter_number
        ).all()

    # READ — all chapters by ISBN
    def list_chapters_by_isbn(self, db: Session, isbn: str) -> list[Book]:
        chapters = (
            db.query(Book).filter(Book.isbn == isbn).order_by(Book.chapter_number).all()
        )
        if not chapters:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chapters found for ISBN {isbn}",
            )
        return chapters

    # UPDATE — specific fields only
    def update_book_fields(
        self,
        db: Session,
        book_id: uuid.UUID,
        summary: Optional[dict] = None,
        qa_bank: Optional[dict] = None,
        quiz: Optional[dict] = None,
        ppt_structure: Optional[dict] = None,
        chapter_title: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> Book:
        book = self.get_by_id(db, book_id)

        if summary is not None:
            book.summary = summary
        if qa_bank is not None:
            book.qa_bank = qa_bank
        if quiz is not None:
            book.quiz = quiz
        if ppt_structure is not None:
            book.ppt_structure = ppt_structure
        if chapter_title is not None:
            book.chapter_title = chapter_title
        if isbn is not None:
            book.isbn = isbn

        db.commit()
        db.refresh(book)
        return book

    # DELETE
    def delete_book(self, db: Session, book_id: uuid.UUID) -> dict:
        book = self.get_by_id(db, book_id)
        db.delete(book)
        db.commit()
        return {"message": f"Book {book_id} deleted successfully"}

    # Internal
    def _find(
        self,
        db: Session,
        book_name: str,
        class_grade: int,
        subject: str,
        chapter_number: int,
    ) -> Optional[Book]:
        return (
            db.query(Book)
            .filter(
                Book.book_name == book_name.strip(),
                Book.class_grade == class_grade,
                Book.subject == subject.lower().strip(),
                Book.chapter_number == chapter_number,
            )
            .first()
        )


class ClassChapterService:
    # CREATE — assign a global book chapter to a class
    def assign_to_class(
        self,
        db: Session,
        school_id: uuid.UUID,
        class_id: uuid.UUID,
        book_id: uuid.UUID,
        teacher_id: uuid.UUID,
        chapter_title: str,
        subject: str,
    ) -> ClassChapter:
        existing = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == class_id,
                ClassChapter.book_id == book_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This chapter is already assigned to this class",
            )

        chapter = ClassChapter(
            school_id=school_id,
            class_id=class_id,
            book_id=book_id,
            teacher_id=teacher_id,
            chapter_title=chapter_title,
            subject=subject,
            custom_summary=None,
            custom_qa_bank=None,
            custom_quiz=None,
            custom_ppt_structure=None,
            is_summary_overridden=False,
            is_qa_bank_overridden=False,
            is_quiz_overridden=False,
            is_ppt_overridden=False,
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        return chapter

    # READ — teacher view (all chapters for a class, published + unpublished)
    # Only the assigned teacher or school admin should call this
    def list_for_teacher(self, db: Session, class_id: uuid.UUID) -> list[ClassChapter]:
        return (
            db.query(ClassChapter)
            .filter(ClassChapter.class_id == class_id)
            .order_by(ClassChapter.subject, ClassChapter.chapter_title)
            .all()
        )

    # READ — resolved content (teacher view — works for draft + published)
    # Always call this, never read fields directly
    def get_resolved_content(self, db: Session, class_chapter_id: uuid.UUID) -> dict:
        chapter = self._get_or_404(db, class_chapter_id)
        book = chapter.book

        return {
            "class_chapter_id": str(chapter.class_chapter_id),
            "chapter_title": chapter.chapter_title,
            "subject": chapter.subject,
            "summary": (
                chapter.custom_summary
                if chapter.is_summary_overridden
                else (book.summary if book else None)
            ),
            "qa_bank": (
                chapter.custom_qa_bank
                if chapter.is_qa_bank_overridden
                else (book.qa_bank if book else None)
            ),
            "quiz": (
                chapter.custom_quiz
                if chapter.is_quiz_overridden
                else (book.quiz if book else None)
            ),
            "ppt_structure": (
                chapter.custom_ppt_structure
                if chapter.is_ppt_overridden
                else (book.ppt_structure if book else None)
            ),
            "overrides": {
                "summary": chapter.is_summary_overridden,
                "qa_bank": chapter.is_qa_bank_overridden,
                "quiz": chapter.is_quiz_overridden,
                "ppt_structure": chapter.is_ppt_overridden,
            },
            "is_published": chapter.published_date is not None,
            "published_date": chapter.published_date,
            "last_modified_date": chapter.last_modified_date,
        }

    # READ — student view
    # 1. Verifies student is enrolled in this class
    # 2. Verifies chapter is published
    # 3. Returns resolved content
    def get_content_for_student(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> dict:
        chapter = self._get_or_404(db, class_chapter_id)

        # Check enrollment
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.class_id == chapter.class_id,
                Enrollment.is_active,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        # Check published
        if not chapter.published_date:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This chapter has not been published yet",
            )

        return self.get_resolved_content(db, class_chapter_id)

    # READ — list published chapters for a student's class
    def list_published_for_student(
        self,
        db: Session,
        class_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> list[dict]:

        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.class_id == class_id,
                Enrollment.is_active,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        chapters = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == class_id,
                ClassChapter.published_date is not None,
            )
            .order_by(ClassChapter.subject, ClassChapter.chapter_title)
            .all()
        )

        return [self.get_resolved_content(db, ch.class_chapter_id) for ch in chapters]

    # UPDATE — teacher overrides, one field at a time
    # global `books` table is NEVER touched here
    def override_summary(
        self, db: Session, class_chapter_id: uuid.UUID, summary: dict
    ) -> ClassChapter:
        chapter = self._get_or_404(db, class_chapter_id)
        chapter.custom_summary = summary
        chapter.is_summary_overridden = True
        db.commit()
        db.refresh(chapter)
        return chapter

    def override_qa_bank(
        self, db: Session, class_chapter_id: uuid.UUID, qa_bank: dict
    ) -> ClassChapter:
        chapter = self._get_or_404(db, class_chapter_id)
        chapter.custom_qa_bank = qa_bank
        chapter.is_qa_bank_overridden = True
        db.commit()
        db.refresh(chapter)
        return chapter

    def override_quiz(
        self, db: Session, class_chapter_id: uuid.UUID, quiz: dict
    ) -> ClassChapter:
        chapter = self._get_or_404(db, class_chapter_id)
        chapter.custom_quiz = quiz
        chapter.is_quiz_overridden = True
        db.commit()
        db.refresh(chapter)
        return chapter

    def override_ppt_structure(
        self, db: Session, class_chapter_id: uuid.UUID, ppt_structure: dict
    ) -> ClassChapter:
        chapter = self._get_or_404(db, class_chapter_id)
        chapter.custom_ppt_structure = ppt_structure
        chapter.is_ppt_overridden = True
        db.commit()
        db.refresh(chapter)
        return chapter

    # UPDATE — reset overrides back to global book content
    def reset_overrides(
        self,
        db: Session,
        class_chapter_id: uuid.UUID,
        fields: list[str],
    ) -> ClassChapter:
        chapter = self._get_or_404(db, class_chapter_id)

        if "summary" in fields:
            chapter.custom_summary = None
            chapter.is_summary_overridden = False
        if "qa_bank" in fields:
            chapter.custom_qa_bank = None
            chapter.is_qa_bank_overridden = False
        if "quiz" in fields:
            chapter.custom_quiz = None
            chapter.is_quiz_overridden = False
        if "ppt_structure" in fields:
            chapter.custom_ppt_structure = None
            chapter.is_ppt_overridden = False

        db.commit()
        db.refresh(chapter)
        return chapter

    # UPDATE — publish chapter so students can see it
    def publish_chapter(self, db: Session, class_chapter_id: uuid.UUID) -> dict:
        chapter = self._get_or_404(db, class_chapter_id)
        chapter.published_date = datetime.now(timezone.utc)
        db.commit()
        db.refresh(chapter)
        return {
            "message": "Chapter published successfully",
            "published_date": chapter.published_date,
        }

    # UPDATE — unpublish chapter (hide from students again)
    def unpublish_chapter(self, db: Session, class_chapter_id: uuid.UUID) -> dict:
        chapter = self._get_or_404(db, class_chapter_id)
        chapter.published_date = None
        db.commit()
        return {"message": "Chapter unpublished successfully"}

    # DELETE — unassign a chapter from a class
    def delete_class_chapter(self, db: Session, class_chapter_id: uuid.UUID) -> dict:
        chapter = self._get_or_404(db, class_chapter_id)
        db.delete(chapter)
        db.commit()
        return {"message": f"ClassChapter {class_chapter_id} removed successfully"}

    # Internal
    def _get_or_404(self, db: Session, class_chapter_id: uuid.UUID) -> ClassChapter:
        chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == class_chapter_id)
            .first()
        )
        if not chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ClassChapter not found"
            )
        return chapter
