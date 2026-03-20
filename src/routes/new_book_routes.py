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
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from src.db.main import get_db
from src.db.models import User
from src.services.db_services.book_service import BookService, ClassChapterService
from src.services.ai_services.book_ingestion_services import BookIngestionService
from src.utils.pdf_extractor import PDFExtractor
from src.utils.jwt_handler import get_current_user, require_role
from src.models.books_schema import UpdateBookFieldsRequest

book_service = BookService()
chapter_service = ClassChapterService()
ai_service = BookIngestionService()

router = APIRouter(prefix="/books", tags=["Global Books"])


# INGEST — Upload PDF → AI generates all content → saved to DB in one step
@router.post(
    "/ingest-book",
    status_code=201,
    summary="Upload PDF, generate all content via AI, save to DB [sudo_admin only]",
    description=(
        "Full pipeline in one endpoint: "
        "1. Extract text from PDF "
        "2. AI generates summary, qa_bank, quiz, ppt_structure "
        "3. Save everything to global books table "
        "Returns 409 if book_name + class_grade + subject + chapter_number already exists."
    ),
)
async def ingest_book(
    board: str = Form(...),
    file: UploadFile = File(...),
    book_name: str = Form(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    isbn: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    # save uploaded PDF to /tmp
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

    # Step 1 — AI service ingests PDF and generates all 4 content types
    # ingest_book returns: { summary, qa_bank, quiz, ppt_structure, scraped_chapter }
    generated = ai_service.ingest_book(file_path, metadata)

    # Step 2 — Save generated content to DB
    book = book_service.create_book(
        db=db,
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


# READ Global Books
@router.get(
    "/",
    summary="List global books [all roles]",
)
def list_books(
    book_name: Optional[str] = None,
    class_grade: Optional[int] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.list_books(
        db, book_name=book_name, class_grade=class_grade, subject=subject
    )


@router.get(
    "/search",
    summary="Get a chapter by book_name + class_grade + subject + chapter_number [all roles]",
)
def get_book_by_metadata(
    book_name: str,
    class_grade: int,
    subject: str,
    chapter_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.get_by_metadata(
        db, book_name, class_grade, subject, chapter_number
    )


@router.get(
    "/isbn/{isbn}",
    summary="Get all chapters of a textbook by ISBN [all roles]",
)
def list_chapters_by_isbn(
    isbn: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.list_chapters_by_isbn(db, isbn)


@router.get(
    "/{book_id}",
    summary="Get a global book by ID [all roles]",
)
def get_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.get_by_id(db, book_id)


# UPDATE / DELETE
@router.patch(
    "/{book_id}",
    summary="Update specific fields of a global book [sudo_admin only]",
)
def update_book(
    book_id: uuid.UUID,
    data: UpdateBookFieldsRequest,
    db: Session = Depends(get_db),
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

    return book_service.update_book_fields(
        db=db,
        book_id=book_id,
        summary=data.summary,
        qa_bank=data.qa_bank,
        quiz=data.quiz,
        ppt_structure=data.ppt_structure,
        chapter_title=data.chapter_title,
        isbn=data.isbn,
    )


@router.delete(
    "/{book_id}",
    summary="Delete a global book [sudo_admin only]",
)
def delete_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sudo_admin")),
):
    return book_service.delete_book(db, book_id)


# TESTING ROUTES (FOR DEVELOPEMENT PURPOSES ONLY)

# /books/test — Debug/test routes (AI only, no DB save)
# Use these to inspect generated content before committing to DB
# Remove or protect these in production


@router.post(
    "/test/extract-text",
    summary="[DEBUG] Extract text from PDF only — no AI, no DB",
)
async def test_extract_text(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("sudo_admin")),
):
    os.makedirs("/tmp", exist_ok=True)
    file_path = f"/tmp/{uuid.uuid4()}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chapter_text = PDFExtractor.extract_text(file_path)
        return {
            "status": "success",
            "text_length": len(chapter_text),
            "preview": chapter_text[:500],
            "message": "Text extracted successfully",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post(
    "/test/summary",
    summary="[DEBUG] Generate summary only — no DB save",
)
async def test_summary(
    file: UploadFile = File(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    current_user: User = Depends(require_role("sudo_admin")),
):
    os.makedirs("/tmp", exist_ok=True)
    file_path = f"/tmp/{uuid.uuid4()}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chapter_text = PDFExtractor.extract_text(file_path)
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": "",
        }
        result = ai_service.generate_summary(chapter_text, metadata)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post(
    "/test/quiz",
    summary="[DEBUG] Generate quiz from summary — no DB save",
)
async def test_quiz(
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    chapter_summary: str = Form(...),
    current_user: User = Depends(require_role("sudo_admin")),
):
    try:
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": "",
        }
        result = ai_service.generate_quiz(chapter_summary, metadata)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post(
    "/test/ppt",
    summary="[DEBUG] Generate PPT structure from summary — no DB save",
)
async def test_ppt(
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    chapter_summary: str = Form(...),
    current_user: User = Depends(require_role("sudo_admin")),
):
    try:
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": "",
        }
        result = ai_service.generate_ppt(chapter_summary, metadata)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post(
    "/test/exercise-extraction",
    summary="[DEBUG] Extract exercises from PDF — no DB save",
)
async def test_exercise_extraction(
    file: UploadFile = File(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    current_user: User = Depends(require_role("sudo_admin")),
):
    os.makedirs("/tmp", exist_ok=True)
    file_path = f"/tmp/{uuid.uuid4()}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chapter_text = PDFExtractor.extract_text(file_path)
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": "",
        }
        result = ai_service.extract_questions_answers(chapter_text, metadata)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post(
    "/test/exercise-answering",
    summary="[DEBUG] Answer extracted exercises — no DB save",
)
async def test_exercise_answering(
    file: UploadFile = File(...),
    questions_json: str = Form(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    current_user: User = Depends(require_role("sudo_admin")),
):
    import json

    os.makedirs("/tmp", exist_ok=True)
    file_path = f"/tmp/{uuid.uuid4()}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chapter_text = PDFExtractor.extract_text(file_path)
        questions = json.loads(questions_json)
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": "",
        }
        result = ai_service.generate_answers(
            chapter_text=chapter_text,
            questions=questions,
            metadata=metadata,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
