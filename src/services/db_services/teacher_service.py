import uuid
import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from src.db.models import User, Class, ClassTeacher, ClassChapter, Enrollment, Book
from src.models.books_schema import EditChapterContentRequest, PublishContentRequest


class TeacherService:
    # DASHBOARD
    async def get_dashboard(self, db: AsyncSession, teacher: User) -> dict:
        assigned_classes = await self._get_assigned_classes(db, teacher.user_id)

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

            # published count
            published_result = await db.execute(
                select(func.count(ClassChapter.class_chapter_id)).where(
                    ClassChapter.class_id == class_.class_id,
                    ClassChapter.teacher_id == teacher.user_id,
                    ClassChapter.published_date.isnot(None),
                )
            )
            published_count = published_result.scalar()

            # total count
            total_result = await db.execute(
                select(func.count(ClassChapter.class_chapter_id)).where(
                    ClassChapter.class_id == class_.class_id,
                    ClassChapter.teacher_id == teacher.user_id,
                )
            )
            total_count = total_result.scalar()

            # student count
            student_result = await db.execute(
                select(func.count(Enrollment.enrollment_id)).where(
                    Enrollment.class_id == class_.class_id,
                    Enrollment.is_active == True,
                )
            )
            student_count = student_result.scalar()

            classes_data.append(
                {
                    "class_id": str(class_.class_id),
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

    # CHAPTERS — all chapters for a class
    async def get_chapters_for_class(
        self, db: AsyncSession, teacher: User, class_id: uuid.UUID
    ) -> dict:
        assignment = await self._get_assignment_or_403(db, teacher.user_id, class_id)

        result = await db.execute(
            select(ClassChapter)
            .where(
                ClassChapter.class_id == class_id,
                ClassChapter.teacher_id == teacher.user_id,
            )
            .order_by(ClassChapter.subject, ClassChapter.chapter_number)
        )
        chapters = result.scalars().all()

        return {
            "class_id": str(class_id),
            "subject": assignment.subject,
            "chapters": [
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "chapter_number": ch.chapter_number,
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

    # AVAILABLE BOOKS
    async def get_available_books(
        self, db: AsyncSession, teacher: User, class_id: uuid.UUID
    ) -> dict:
        assignment = await self._get_assignment_or_403(db, teacher.user_id, class_id)

        class_result = await db.execute(select(Class).where(Class.class_id == class_id))
        class_ = class_result.scalar_one_or_none()

        # build book query
        book_query = select(Book).where(Book.class_grade == class_.grade_level)
        if assignment.subject:
            book_query = book_query.where(
                Book.subject == assignment.subject.lower().strip()
            )
        book_query = book_query.order_by(Book.book_name, Book.chapter_number)

        books_result = await db.execute(book_query)
        books = books_result.scalars().all()

        # collect already assigned book_ids in one query
        assigned_result = await db.execute(
            select(ClassChapter.book_id).where(ClassChapter.class_id == class_id)
        )
        assigned_book_ids = {str(row) for row in assigned_result.scalars().all() if row}

        return {
            "class_id": str(class_id),
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

    # -----------------------------------------------------------------------
    # INTERNAL HELPERS
    # -----------------------------------------------------------------------
    async def _get_assigned_classes(
        self, db: AsyncSession, teacher_id: uuid.UUID
    ) -> list[ClassTeacher]:
        result = await db.execute(
            select(ClassTeacher)
            .where(ClassTeacher.teacher_id == teacher_id)
            .options(
                joinedload(ClassTeacher.class_).joinedload(Class.school)
            )  # needed for ct.class_.school in dashboard
        )
        return result.scalars().all()

    async def _get_assignment_or_403(
        self, db: AsyncSession, teacher_id: uuid.UUID, class_id: uuid.UUID
    ) -> ClassTeacher:
        result = await db.execute(
            select(ClassTeacher).where(
                ClassTeacher.class_id == class_id,
                ClassTeacher.teacher_id == teacher_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this class",
            )
        return assignment

    def _teacher_profile(self, teacher: User) -> dict:
        # no DB access — stays plain def
        return {
            "user_id": str(teacher.user_id),
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "email": teacher.email,
            "is_password_changed": teacher.is_password_changed,
        }

    async def get_book_names(
        self, db: AsyncSession, grade_level: int, subject: str
    ) -> list[str]:
        result = await db.execute(
            select(Book.book_name)
            .where(
                Book.class_grade == grade_level,
                Book.subject == subject.lower().strip(),
            )
            .distinct()
            .order_by(Book.book_name)
        )
        return result.scalars().all()

    async def get_chapter_content(
        self,
        db: AsyncSession,
        book_name: str,
        class_grade: int,
        subject: str,
        chapter_number: int,
        content_type: str,
    ) -> dict:
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        result = await db.execute(
            select(Book).where(
                Book.book_name == book_name,
                Book.class_grade == class_grade,
                Book.subject == subject.lower().strip(),
                Book.chapter_number == chapter_number,
            )
        )
        book = result.scalar_one_or_none()
        if not book:
            raise HTTPException(status_code=404, detail="Chapter not found")

        return {
            "book_name": book.book_name,
            "chapter_number": book.chapter_number,
            "chapter_title": book.chapter_title,
            "class_grade": book.class_grade,
            "subject": book.subject,
            "content_type": content_type,
            "content": getattr(book, content_type),
        }

    async def edit_chapter_content(
        self, db: AsyncSession, teacher: User, data: EditChapterContentRequest
    ) -> dict:
        await self._get_assignment_or_403(db, teacher.user_id, data.class_id)

        class_result = await db.execute(
            select(Class).where(Class.class_id == data.class_id)
        )
        class_obj = class_result.scalar_one_or_none()
        if not class_obj:
            raise HTTPException(status_code=404, detail="Class not found")

        school_id = class_obj.school_id

        book_result = await db.execute(
            select(Book).where(
                Book.book_name == data.book_name,
                Book.class_grade == data.class_grade,
                Book.subject == data.subject.lower().strip(),
                Book.chapter_number == data.chapter_number,
            )
        )
        book = book_result.scalar_one_or_none()
        if not book:
            raise HTTPException(status_code=404, detail="Book chapter not found")

        chapter_result = await db.execute(
            select(ClassChapter).where(
                ClassChapter.class_id == data.class_id,
                ClassChapter.book_id == book.book_id,
                ClassChapter.chapter_number == data.chapter_number,
                ClassChapter.teacher_id == teacher.user_id,
            )
        )
        class_chapter = chapter_result.scalar_one_or_none()

        if not class_chapter:
            class_chapter = ClassChapter(
                school_id=school_id,
                class_id=data.class_id,
                book_id=book.book_id,
                chapter_number=data.chapter_number,
                teacher_id=teacher.user_id,
                subject=data.subject,
                custom_summary=None,
                custom_qa_bank=None,
                custom_quiz=None,
                custom_ppt_structure=None,
                is_summary_overridden=False,
                is_qa_bank_overridden=False,
                is_quiz_overridden=False,
                is_ppt_overridden=False,
            )
            db.add(class_chapter)
            await db.commit()
            await db.refresh(class_chapter)

        content_field = f"custom_{data.content_type}"
        custom_content = getattr(class_chapter, content_field)

        if custom_content:
            editable_content = custom_content
            is_overridden = True
        else:
            editable_content = getattr(book, data.content_type)
            is_overridden = False

        return {
            "class_chapter_id": str(class_chapter.class_chapter_id),
            "book_name": book.book_name,
            "chapter_number": book.chapter_number,
            "chapter_title": book.chapter_title,
            "class_grade": book.class_grade,
            "subject": book.subject,
            "content_type": data.content_type,
            "editable_content": editable_content,
            "is_overridden": is_overridden,
        }

    async def publish_chapter_content(
        self, db: AsyncSession, teacher: User, data: PublishContentRequest
    ) -> dict:

        if data.class_chapter_id:
            chapter_result = await db.execute(
                select(ClassChapter).where(
                    ClassChapter.class_chapter_id == data.class_chapter_id
                )
            )
            class_chapter = chapter_result.scalar_one_or_none()
            if not class_chapter:
                raise HTTPException(status_code=404, detail="ClassChapter not found")
        else:
            if not all(
                [
                    data.class_id,
                    data.book_name,
                    data.class_grade,
                    data.subject,
                    data.chapter_number,
                ]
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Either class_chapter_id OR complete chapter metadata required",
                )

            await self._get_assignment_or_403(db, teacher.user_id, data.class_id)

            book_result = await db.execute(
                select(Book).where(
                    Book.book_name == data.book_name,
                    Book.class_grade == data.class_grade,
                    Book.subject == data.subject.lower().strip(),
                    Book.chapter_number == data.chapter_number,
                )
            )
            book = book_result.scalar_one_or_none()
            if not book:
                raise HTTPException(status_code=404, detail="Book chapter not found")

            class_result = await db.execute(
                select(Class).where(Class.class_id == data.class_id)
            )
            class_obj = class_result.scalar_one_or_none()
            if not class_obj:
                raise HTTPException(status_code=404, detail="Class not found")

            school_id = class_obj.school_id

            chapter_result = await db.execute(
                select(ClassChapter).where(
                    ClassChapter.class_id == data.class_id,
                    ClassChapter.book_id == book.book_id,
                    ClassChapter.chapter_number == data.chapter_number,
                    ClassChapter.teacher_id == teacher.user_id,
                )
            )
            class_chapter = chapter_result.scalar_one_or_none()

            if not class_chapter:
                class_chapter = ClassChapter(
                    school_id=school_id,
                    class_id=data.class_id,
                    book_id=book.book_id,
                    chapter_number=data.chapter_number,
                    teacher_id=teacher.user_id,
                    subject=data.subject,
                )
                db.add(class_chapter)
                await db.flush()

        # update content
        content_field = f"custom_{data.content_type}"
        override_flag = f"is_{data.content_type}_overridden"

        setattr(class_chapter, content_field, data.content)
        setattr(class_chapter, override_flag, True)
        class_chapter.published_date = datetime.datetime.now(datetime.timezone.utc)

        await db.commit()
        await db.refresh(class_chapter)

        return {
            "message": f"{data.content_type} published successfully",
            "class_chapter_id": str(class_chapter.class_chapter_id),
            "content_type": data.content_type,
            "published_date": class_chapter.published_date,
        }

    async def get_published_content_list(
        self,
        db: AsyncSession,
        teacher: User,
        class_id: uuid.UUID,
        content_type: str,
    ) -> dict:
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        assignment = await self._get_assignment_or_403(db, teacher.user_id, class_id)

        class_result = await db.execute(select(Class).where(Class.class_id == class_id))
        class_ = class_result.scalar_one_or_none()
        if not class_:
            raise HTTPException(status_code=404, detail="Class not found")

        override_flag = f"is_{content_type}_overridden"

        chapters_result = await db.execute(
            select(ClassChapter)
            .where(
                ClassChapter.class_id == class_id,
                ClassChapter.teacher_id == teacher.user_id,
                ClassChapter.published_date.isnot(None),
                getattr(ClassChapter, override_flag) == True,
            )
            .order_by(ClassChapter.published_date.desc())
        )
        chapters = chapters_result.scalars().all()

        # fetch all books for these chapters in one query — no N+1
        book_ids = [ch.book_id for ch in chapters if ch.book_id]
        books_result = await db.execute(select(Book).where(Book.book_id.in_(book_ids)))
        book_map = {b.book_id: b for b in books_result.scalars().all()}

        return {
            "class_id": str(class_id),
            "subject": assignment.subject,
            "content_type": content_type,
            "total_published": len(chapters),
            "published_content": [
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "book_name": book_map[ch.book_id].book_name
                    if ch.book_id and ch.book_id in book_map
                    else None,
                    "chapter_number": ch.chapter_number,
                    "published_date": ch.published_date,
                    "is_overridden": getattr(ch, override_flag),
                }
                for ch in chapters
            ],
        }
