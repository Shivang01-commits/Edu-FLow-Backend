import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.db.models import User, Class, ClassTeacher, ClassChapter, Enrollment, Book
from src.models.books_schema import EditChapterContentRequest, PublishContentRequest
import datetime


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

    def get_book_names(self, db: Session, grade_level: int, subject: str) -> list[str]:
        results = (
            db.query(Book.book_name)
            .filter(
                Book.class_grade == grade_level,
                Book.subject == subject.lower().strip(),
            )
            .distinct()
            .order_by(Book.book_name)
            .all()
        )
        return [r[0] for r in results]

    def get_chapter_content(
        self,
        db: Session,
        book_name: str,
        class_grade: int,
        subject: str,
        chapter_number: int,
        content_type: str,
    ) -> dict:

        # Validate content_type
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}",
            )

        # Query the book
        book = (
            db.query(Book)
            .filter(
                Book.book_name == book_name,
                Book.class_grade == class_grade,
                Book.subject == subject.lower().strip(),
                Book.chapter_number == chapter_number,
            )
            .first()
        )

        if not book:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Return the requested content
        return {
            "book_name": book.book_name,
            "chapter_number": book.chapter_number,
            "chapter_title": book.chapter_title,
            "class_grade": book.class_grade,
            "subject": book.subject,
            "content_type": content_type,
            content_type: getattr(book, content_type),  # Get the column dynamically
        }

    # edit chapter content ----------------------- ----------------------
    def edit_chapter_content(
        self, db: Session, teacher: User, data: EditChapterContentRequest
    ) -> dict:

        # Step 1: Verify teacher is assigned to this class
        self._get_assignment_or_403(db, teacher.user_id, data.class_id)

        class_obj = db.query(Class).filter(Class.class_id == data.class_id).first()

        if not class_obj:
            raise HTTPException(status_code=404, detail="Class not found")

        school_id = class_obj.school_id

        book = (
            db.query(Book)
            .filter(
                Book.book_name == data.book_name,
                Book.class_grade == data.class_grade,
                Book.subject == data.subject.lower().strip(),
                Book.chapter_number == data.chapter_number,
            )
            .first()
        )

        if not book:
            raise HTTPException(status_code=404, detail="Book chapter not found")

        # Step 3: Check if ClassChapter exists, if not create it
        class_chapter = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == data.class_id,
                ClassChapter.book_id == book.book_id,
                ClassChapter.chapter_number == data.chapter_number,
                ClassChapter.teacher_id == teacher.user_id,
            )
            .first()
        )

        if not class_chapter:
            # Create new ClassChapter
            class_chapter = ClassChapter(
                school_id=school_id,
                class_id=data.class_id,
                book_id=book.book_id,
                chapter_number=data.chapter_number,
                teacher_id=teacher.user_id,
                # chapter_title=data.chapter_title,
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
            db.commit()
            db.refresh(class_chapter)

        # Step 4: Get the content to edit
        # If custom content exists, use it; otherwise use global book content
        content_field = f"custom_{data.content_type}"
        custom_content = getattr(class_chapter, content_field)

        if custom_content:
            # Teacher already customized this, show custom version
            editable_content = custom_content
            is_overridden = True
        else:
            # First time editing, show global book content
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
            "is_overridden": is_overridden,  # True if teacher already customized
        }

    def publish_chapter_content(
        self, db: Session, teacher: User, data: PublishContentRequest
    ) -> dict:

        # Step 1: Get or create ClassChapter
        if data.class_chapter_id:
            # Path 1: class_chapter_id provided (came from EDIT)
            class_chapter = (
                db.query(ClassChapter)
                .filter(ClassChapter.class_chapter_id == data.class_chapter_id)
                .first()
            )
            if not class_chapter:
                raise HTTPException(status_code=404, detail="ClassChapter not found")
        else:
            # Path 2: chapter metadata provided (direct publish)
            if not all(
                [
                    data.class_id,
                    data.book_name,
                    data.class_grade,
                    data.subject,
                    data.chapter_number,
                    # data.chapter_title,
                ]
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Either class_chapter_id OR complete chapter metadata required",
                )

            # Verify teacher is assigned to this class
            assignment = self._get_assignment_or_403(db, teacher.user_id, data.class_id)

            # Find the global book chapter
            book = (
                db.query(Book)
                .filter(
                    Book.book_name == data.book_name,
                    Book.class_grade == data.class_grade,
                    Book.subject == data.subject.lower().strip(),
                    Book.chapter_number == data.chapter_number,
                )
                .first()
            )

            if not book:
                raise HTTPException(status_code=404, detail="Book chapter not found")

            class_obj = db.query(Class).filter(Class.class_id == data.class_id).first()

            if not class_obj:
                raise HTTPException(status_code=404, detail="Class not found")

            school_id = class_obj.school_id
            # Get or create ClassChapter
            class_chapter = (
                db.query(ClassChapter)
                .filter(
                    ClassChapter.class_id == data.class_id,
                    ClassChapter.book_id == book.book_id,
                    ClassChapter.chapter_number == data.chapter_number,
                    ClassChapter.teacher_id == teacher.user_id,
                )
                .first()
            )

            if not class_chapter:
                class_chapter = ClassChapter(
                    school_id=school_id,
                    class_id=data.class_id,
                    book_id=book.book_id,
                    chapter_number=data.chapter_number,
                    teacher_id=teacher.user_id,
                    # chapter_title=data.chapter_title,
                    subject=data.subject,
                )
                db.add(class_chapter)
                db.flush()

        # Step 2: Update content
        content_field = f"custom_{data.content_type}"
        override_flag = f"is_{data.content_type}_overridden"

        setattr(class_chapter, content_field, data.content)
        setattr(class_chapter, override_flag, True)
        class_chapter.published_date = datetime.datetime.now()

        db.commit()
        db.refresh(class_chapter)

        return {
            "message": f"{data.content_type} published successfully",
            "class_chapter_id": str(class_chapter.class_chapter_id),
            "content_type": data.content_type,
            "published_date": class_chapter.published_date,
        }


    def get_published_content_list(
        self,
        db: Session,
        teacher: User,
        class_id: uuid.UUID,
        content_type: str
    ) -> dict:
        from sqlalchemy import and_
        
        # Step 1: Validate content_type
        allowed_types = {"summary", "quiz", "qa_bank", "ppt_structure"}
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid content_type. Allowed: {allowed_types}"
            )
        
        # Step 2: Verify teacher is assigned to this class
        assignment = self._get_assignment_or_403(db, teacher.user_id, class_id)
        
        # Step 3: Get class info
        class_ = db.query(Class).filter(Class.class_id == class_id).first()
        if not class_:
            raise HTTPException(status_code=404, detail="Class not found")
        
        # Step 4: Build the override flag column name
        override_flag = f"is_{content_type}_overridden"
        
        # Step 5: Query ClassChapter records where this content type is published
        chapters = (
            db.query(ClassChapter)
            .filter(
                ClassChapter.class_id == class_id,
                ClassChapter.teacher_id == teacher.user_id,
                ClassChapter.published_date.isnot(None),
                getattr(ClassChapter, override_flag) == True
            )
            .order_by(ClassChapter.published_date.desc())
            .all()
        )
        
        # Step 6: Build response
        content_list = []
        for ch in chapters:
            book = db.query(Book).filter(Book.book_id == ch.book_id).first()
            content_list.append(
                {
                    "class_chapter_id": str(ch.class_chapter_id),
                    "book_name": book.book_name if book else None,
                    "chapter_number": ch.chapter_number,
                    "published_date": ch.published_date,
                    "is_overridden": getattr(ch, override_flag),
                }
            )
        
        return {
            "class_id": str(class_id),
            "class_name": class_.class_name,
            "subject": assignment.subject,
            "content_type": content_type,
            "total_published": len(content_list),
            "published_content": content_list,
        }