"""
Flow:
  sudo_admin uploads PDF
      ↓
  AI service extracts text + generates summary, quiz, qa_bank, ppt_structure
      ↓
  Generated content saved to global `books` table via book_service.create_book()
      ↓
  Returns the saved Book object with book_id

"""

import os
import uuid
import shutil
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    BackgroundTasks,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.teacher_service import TeacherService
from src.services.db_services.book_service import BookService, ClassChapterService
from src.services.ai_services.book_ingestion_services import BookIngestionService
from src.utils.jwt_handler import get_current_user, require_role
from src.models.books_schema import UpdateBookFieldsRequest
from src.models.presentation_schema import GeneratePresentationRequest
from src.services.ai_services.presentation_service import PresentationService


book_service = BookService()
chapter_service = ClassChapterService()
ai_service = BookIngestionService()
teacher_service = TeacherService()
presentation_service = PresentationService()

router = APIRouter(prefix="/books", tags=["Global Books"])


@router.post("/ingest-book", status_code=201)
async def ingest_book(
    board: str = Form(...),
    file: UploadFile = File(...),
    book_name: str = Form(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    isbn: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    os.makedirs("/tmp", exist_ok=True)
    file_path = f"/tmp/{uuid.uuid4()}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    metadata = {
        "board": board,
        "book_name": book_name,
        "class_grade": class_grade,
        "subject": subject,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "isbn": isbn,
    }

    generated = ai_service.ingest_book(file_path, metadata)

    book = await book_service.create_book(
        db=db,
        board=board,
        book_name=book_name,
        class_grade=class_grade,
        subject=subject,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        scraped_chapter=generated.get("scraped_chapter"),
        summary=generated.get("summary"),
        qa_bank=generated.get("qa_bank"),
        quiz=generated.get("quiz"),
        ppt_structure=generated.get("ppt_structure"),
        isbn=isbn if isbn else None,
    )

    return {
        "message": "Book ingested and saved successfully",
        "book": book,
    }


@router.get("/")
async def list_books(
    book_name: Optional[str] = None,
    class_grade: Optional[int] = None,
    subject: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await book_service.list_books(
        db, book_name=book_name, class_grade=class_grade, subject=subject
    )


@router.get("/search")
async def get_book_by_metadata(
    book_name: str,
    class_grade: int,
    subject: str,
    chapter_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await book_service.get_by_metadata(
        db, book_name, class_grade, subject, chapter_number
    )


@router.get("/isbn/{isbn}")
async def list_chapters_by_isbn(
    isbn: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await book_service.list_chapters_by_isbn(db, isbn)


@router.get("/{book_id}")
async def get_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await book_service.get_by_id(db, book_id)


@router.patch("/{book_id}")
async def update_book(
    book_id: uuid.UUID,
    data: UpdateBookFieldsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    if not any(
        [
            data.summary,
            data.qa_bank,
            data.quiz,
            data.ppt_structure,
            data.chapter_title,
            data.isbn,
        ]
    ):
        raise HTTPException(status_code=422, detail="No fields provided to update")

    return await book_service.update_book_fields(
        db=db,
        book_id=book_id,
        summary=data.summary,
        qa_bank=data.qa_bank,
        quiz=data.quiz,
        ppt_structure=data.ppt_structure,
        chapter_title=data.chapter_title,
        isbn=data.isbn,
    )


@router.delete("/{book_id}")
async def delete_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await book_service.delete_book(db, book_id)


@router.post("/{book_id}/generate-ppt")
async def generate_book_ppt(
    book_id: uuid.UUID,
    data: GeneratePresentationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return await presentation_service.initiate_ppt_generation(
        db=db,
        book_id=book_id,
        background_tasks=background_tasks,
        template=data.template,
        theme=data.theme,
        language=data.language,
        export_as=data.export_as,
    )


# TESTING ROUTES (FOR DEVELOPEMENT PURPOSES ONLY)

# /books/test — Debug/test routes (AI only, no DB save)
# Use these to inspect generated content before committing to DB
# Remove or protect these in production


# @router.post(
#     "/test/extract-text",
#     summary="[DEBUG] Extract text from PDF only — no AI, no DB",
# )
# async def test_extract_text(
#     file: UploadFile = File(...),
#     current_user: User = Depends(require_role("sudo_admin")),
# ):
#     os.makedirs("/tmp", exist_ok=True)
#     file_path = f"/tmp/{uuid.uuid4()}.pdf"

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         chapter_text = PDFExtractor.extract_text(file_path)
#         return {
#             "status": "success",
#             "text_length": len(chapter_text),
#             "preview": chapter_text[:500],
#             "message": "Text extracted successfully",
#         }
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @router.post(
#     "/test/summary",
#     summary="[DEBUG] Generate summary only — no DB save",
# )
# async def test_summary(
#     file: UploadFile = File(...),
#     class_grade: int = Form(...),
#     subject: str = Form(...),
#     chapter_number: int = Form(...),
#     chapter_title: str = Form(...),
#     current_user: User = Depends(require_role("sudo_admin")),
# ):
#     os.makedirs("/tmp", exist_ok=True)
#     file_path = f"/tmp/{uuid.uuid4()}.pdf"

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         chapter_text = PDFExtractor.extract_text(file_path)
#         metadata = {
#             "class_grade": class_grade,
#             "subject": subject,
#             "chapter_number": chapter_number,
#             "chapter_title": chapter_title,
#             "isbn": "",
#         }
#         result = ai_service.generate_summary(chapter_text, metadata)
#         return {"status": "success", "data": result}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @router.post(
#     "/test/quiz",
#     summary="[DEBUG] Generate quiz from summary — no DB save",
# )
# async def test_quiz(
#     class_grade: int = Form(...),
#     subject: str = Form(...),
#     chapter_number: int = Form(...),
#     chapter_title: str = Form(...),
#     chapter_summary: str = Form(...),
#     current_user: User = Depends(require_role("sudo_admin")),
# ):
#     try:
#         metadata = {
#             "class_grade": class_grade,
#             "subject": subject,
#             "chapter_number": chapter_number,
#             "chapter_title": chapter_title,
#             "isbn": "",
#         }
#         result = ai_service.generate_quiz(chapter_summary, metadata)
#         return {"status": "success", "data": result}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @router.post(
#     "/test/ppt",
#     summary="[DEBUG] Generate PPT structure from summary — no DB save",
# )
# async def test_ppt(
#     class_grade: int = Form(...),
#     subject: str = Form(...),
#     chapter_number: int = Form(...),
#     chapter_title: str = Form(...),
#     chapter_summary: str = Form(...),
#     current_user: User = Depends(require_role("sudo_admin")),
# ):
#     try:
#         metadata = {
#             "class_grade": class_grade,
#             "subject": subject,
#             "chapter_number": chapter_number,
#             "chapter_title": chapter_title,
#             "isbn": "",
#         }
#         result = ai_service.generate_ppt(chapter_summary, metadata)
#         return {"status": "success", "data": result}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @router.post(
#     "/test/exercise-extraction",
#     summary="[DEBUG] Extract exercises from PDF — no DB save",
# )
# async def test_exercise_extraction(
#     file: UploadFile = File(...),
#     class_grade: int = Form(...),
#     subject: str = Form(...),
#     chapter_number: int = Form(...),
#     chapter_title: str = Form(...),
#     current_user: User = Depends(require_role("sudo_admin")),
# ):
#     os.makedirs("/tmp", exist_ok=True)
#     file_path = f"/tmp/{uuid.uuid4()}.pdf"

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         chapter_text = PDFExtractor.extract_text(file_path)
#         metadata = {
#             "class_grade": class_grade,
#             "subject": subject,
#             "chapter_number": chapter_number,
#             "chapter_title": chapter_title,
#             "isbn": "",
#         }
#         result = ai_service.extract_questions_answers(chapter_text, metadata)
#         return {"status": "success", "data": result}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @router.post(
#     "/test/exercise-answering",
#     summary="[DEBUG] Answer extracted exercises — no DB save",
# )
# async def test_exercise_answering(
#     file: UploadFile = File(...),
#     questions_json: str = Form(...),
#     class_grade: int = Form(...),
#     subject: str = Form(...),
#     chapter_number: int = Form(...),
#     chapter_title: str = Form(...),
#     current_user: User = Depends(require_role("sudo_admin")),
# ):
#     import json

#     os.makedirs("/tmp", exist_ok=True)
#     file_path = f"/tmp/{uuid.uuid4()}.pdf"

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     try:
#         chapter_text = PDFExtractor.extract_text(file_path)
#         questions = json.loads(questions_json)
#         metadata = {
#             "class_grade": class_grade,
#             "subject": subject,
#             "chapter_number": chapter_number,
#             "chapter_title": chapter_title,
#             "isbn": "",
#         }
#         result = ai_service.generate_answers(
#             chapter_text=chapter_text,
#             questions=questions,
#             metadata=metadata,
#         )
#         return {"status": "success", "data": result}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
