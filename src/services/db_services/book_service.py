import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import Book, ClassChapter, Enrollment


class BookService:
    async def create_book(
        self,
        db: AsyncSession,
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
        existing = await self._find(db, book_name, class_grade, subject, chapter_number)
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
        await db.commit()
        await db.refresh(book)
        return book

    async def get_by_id(self, db: AsyncSession, book_id: uuid.UUID) -> Book:
        result = await db.execute(select(Book).where(Book.book_id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
        return book

    async def get_by_metadata(
        self,
        db: AsyncSession,
        book_name: str,
        class_grade: int,
        subject: str,
        chapter_number: int,
    ) -> Book:
        book = await self._find(db, book_name, class_grade, subject, chapter_number)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
        return book

    async def list_books(
        self,
        db: AsyncSession,
        book_name: Optional[str] = None,
        class_grade: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> list[Book]:
        query = select(Book)
        if book_name:
            query = query.where(Book.book_name == book_name.strip())
        if class_grade is not None:
            query = query.where(Book.class_grade == class_grade)
        if subject:
            query = query.where(Book.subject == subject.lower().strip())
        query = query.order_by(
            Book.book_name, Book.class_grade, Book.subject, Book.chapter_number
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def list_chapters_by_isbn(self, db: AsyncSession, isbn: str) -> list[Book]:
        result = await db.execute(
            select(Book).where(Book.isbn == isbn).order_by(Book.chapter_number)
        )
        chapters = result.scalars().all()
        if not chapters:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chapters found for ISBN {isbn}",
            )
        return chapters

    async def update_book_fields(
        self,
        db: AsyncSession,
        book_id: uuid.UUID,
        summary: Optional[dict] = None,
        qa_bank: Optional[dict] = None,
        quiz: Optional[dict] = None,
        ppt_structure: Optional[dict] = None,
        chapter_title: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> Book:
        book = await self.get_by_id(db, book_id)

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

        await db.commit()
        await db.refresh(book)
        return book

    async def delete_book(self, db: AsyncSession, book_id: uuid.UUID) -> dict:
        book = await self.get_by_id(db, book_id)
        await db.delete(book)
        await db.commit()
        return {"message": f"Book {book_id} deleted successfully"}

    async def _find(
        self,
        db: AsyncSession,
        book_name: str,
        class_grade: int,
        subject: str,
        chapter_number: int,
    ) -> Optional[Book]:
        result = await db.execute(
            select(Book).where(
                Book.book_name == book_name.strip(),
                Book.class_grade == class_grade,
                Book.subject == subject.lower().strip(),
                Book.chapter_number == chapter_number,
            )
        )
        return result.scalar_one_or_none()


class ClassChapterService:
    async def assign_to_class(
        self,
        db: AsyncSession,
        school_id: uuid.UUID,
        class_id: uuid.UUID,
        book_id: uuid.UUID,
        teacher_id: uuid.UUID,
        chapter_title: str,
        subject: str,
    ) -> ClassChapter:
        existing_result = await db.execute(
            select(ClassChapter).where(
                ClassChapter.class_id == class_id,
                ClassChapter.book_id == book_id,
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This chapter is already assigned to this class",
            )

        chapter = ClassChapter(
            school_id=school_id,
            class_id=class_id,
            book_id=book_id,
            teacher_id=teacher_id,
            subject=subject.lower().strip(),
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
        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def list_for_teacher(
        self, db: AsyncSession, class_id: uuid.UUID
    ) -> list[ClassChapter]:
        result = await db.execute(
            select(ClassChapter)
            .where(ClassChapter.class_id == class_id)
            .order_by(ClassChapter.subject, ClassChapter.chapter_number)
        )
        return result.scalars().all()

    async def get_resolved_content(
        self, db: AsyncSession, class_chapter_id: uuid.UUID
    ) -> dict:
        chapter = await self._get_or_404(db, class_chapter_id)

        # eagerly load book since we access chapter.book
        book_result = await db.execute(
            select(Book).where(Book.book_id == chapter.book_id)
        )
        book = book_result.scalar_one_or_none()

        return {
            "class_chapter_id": str(chapter.class_chapter_id),
            "chapter_number": chapter.chapter_number,
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

    async def get_content_for_student(
        self,
        db: AsyncSession,
        class_chapter_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> dict:
        chapter = await self._get_or_404(db, class_chapter_id)

        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.class_id == chapter.class_id,
                Enrollment.is_active == True,
            )
        )
        if not enrollment_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        if not chapter.published_date:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This chapter has not been published yet",
            )

        return await self.get_resolved_content(db, class_chapter_id)

    async def list_published_for_student(
        self,
        db: AsyncSession,
        class_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> list[dict]:
        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.class_id == class_id,
                Enrollment.is_active == True,
            )
        )
        if not enrollment_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this class",
            )

        chapters_result = await db.execute(
            select(ClassChapter)
            .where(
                ClassChapter.class_id == class_id,
                ClassChapter.published_date.isnot(None),
            )
            .order_by(ClassChapter.subject, ClassChapter.chapter_number)
        )
        chapters = chapters_result.scalars().all()

        # resolve content for each chapter
        return [
            await self.get_resolved_content(db, ch.class_chapter_id) for ch in chapters
        ]

    async def override_summary(
        self, db: AsyncSession, class_chapter_id: uuid.UUID, summary: dict
    ) -> ClassChapter:
        chapter = await self._get_or_404(db, class_chapter_id)
        chapter.custom_summary = summary
        chapter.is_summary_overridden = True
        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def override_qa_bank(
        self, db: AsyncSession, class_chapter_id: uuid.UUID, qa_bank: dict
    ) -> ClassChapter:
        chapter = await self._get_or_404(db, class_chapter_id)
        chapter.custom_qa_bank = qa_bank
        chapter.is_qa_bank_overridden = True
        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def override_quiz(
        self, db: AsyncSession, class_chapter_id: uuid.UUID, quiz: dict
    ) -> ClassChapter:
        chapter = await self._get_or_404(db, class_chapter_id)
        chapter.custom_quiz = quiz
        chapter.is_quiz_overridden = True
        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def override_ppt_structure(
        self, db: AsyncSession, class_chapter_id: uuid.UUID, ppt_structure: dict
    ) -> ClassChapter:
        chapter = await self._get_or_404(db, class_chapter_id)
        chapter.custom_ppt_structure = ppt_structure
        chapter.is_ppt_overridden = True
        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def reset_overrides(
        self,
        db: AsyncSession,
        class_chapter_id: uuid.UUID,
        fields: list[str],
    ) -> ClassChapter:
        chapter = await self._get_or_404(db, class_chapter_id)

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

        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def publish_chapter(
        self, db: AsyncSession, class_chapter_id: uuid.UUID
    ) -> dict:
        chapter = await self._get_or_404(db, class_chapter_id)
        chapter.published_date = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(chapter)
        return {
            "message": "Chapter published successfully",
            "published_date": chapter.published_date,
        }

    async def unpublish_chapter(
        self, db: AsyncSession, class_chapter_id: uuid.UUID
    ) -> dict:
        chapter = await self._get_or_404(db, class_chapter_id)
        chapter.published_date = None
        await db.commit()
        return {"message": "Chapter unpublished successfully"}

    async def delete_class_chapter(
        self, db: AsyncSession, class_chapter_id: uuid.UUID
    ) -> dict:
        chapter = await self._get_or_404(db, class_chapter_id)
        await db.delete(chapter)
        await db.commit()
        return {"message": f"ClassChapter {class_chapter_id} removed successfully"}

    async def _get_or_404(
        self, db: AsyncSession, class_chapter_id: uuid.UUID
    ) -> ClassChapter:
        result = await db.execute(
            select(ClassChapter).where(
                ClassChapter.class_chapter_id == class_chapter_id
            )
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ClassChapter not found",
            )
        return chapter
