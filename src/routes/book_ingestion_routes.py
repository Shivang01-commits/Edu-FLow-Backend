from fastapi import APIRouter, UploadFile, File, Form
import os
import shutil
import uuid
from src.services.ai_services.book_ingestion_services import BookIngestionService
from src.utils.pdf_extractor import PDFExtractor
import json

router = APIRouter(prefix="/books")

service = BookIngestionService()



router.post("/ingest-book")
async def ingest_book(
    file: UploadFile = File(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    isbn: str = Form(...)
):

    file_id = str(uuid.uuid4())
    file_path = f"/tmp/{file_id}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    metadata = {
        "class_grade": class_grade,
        "subject": subject,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "isbn": isbn
    }

    result = service.ingest_book(file_path, metadata)

    return result

# Adding these test routes to Book_routes.py temporarily


router.post("/test/extract-text")
async def test_extract_text(
    file: UploadFile = File(...)
):
    """Test PDF text extraction only"""
    try:

        # Ensure /tmp directory exists
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp", exist_ok=True)

        
        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}.pdf"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        chapter_text = PDFExtractor.extract_text(file_path)
        
        return {
            "status": "success",
            "text_length": len(chapter_text),
            "preview": chapter_text[:500],  # First 500 chars
            "message": "Text extracted successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



router.post("/test/summary")
async def test_summary(
    file: UploadFile = File(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...)
):
    """Test summary generation only"""
    try:
        # Ensure /tmp directory exists
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp", exist_ok=True)


        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}.pdf"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        chapter_text = PDFExtractor.extract_text(file_path)
        
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": ""
        }
        
        result = service.generate_summary(chapter_text, metadata)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



router.post("/test/quiz")
async def test_quiz(
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    chapter_summary: str = Form(...)
):
    """Test quiz generation from summary"""
    try:
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": ""
        }
        
        result = service.generate_quiz(chapter_summary, metadata)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



router.post("/test/ppt")
async def test_ppt(
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...),
    chapter_summary: str = Form(...)
):
    """Test PPT generation from summary"""
    try:
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": ""
        }
        
        result = service.generate_ppt(chapter_summary, metadata)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



router.post("/test/exercise-extraction")
async def test_exercise_extraction(
    file: UploadFile = File(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...)
):
    """Test exercise extraction only"""
    try:

        # Ensure /tmp directory exists
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp", exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}.pdf"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        chapter_text = PDFExtractor.extract_text(file_path)
        
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": ""
        }
        
        result = service.extract_questions_answers(chapter_text, metadata)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



router.post("/test/vboth_exercise-answering")
async def test_exercise_answering(
    file: UploadFile = File(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...)
):
    """Test full exercise extraction + answering"""
    try:

        # Ensure /tmp directory exists
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp", exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}.pdf"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        chapter_text = PDFExtractor.extract_text(file_path)
        
        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": ""
        }
        
        # First extract questions
        extracted = service.extract_questions_answers(chapter_text, metadata)
        
        return {
            "status": "success",
            "data": extracted
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    


router.post("/test/exercise-answering")
async def test_exercise_answering(
    file: UploadFile = File(...),
    questions_json: str = Form(...),
    class_grade: int = Form(...),
    subject: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...)
):
    """Test exercise answering"""

    try:

        # Ensure /tmp directory exists
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp", exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}.pdf"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract chapter text
        chapter_text = PDFExtractor.extract_text(file_path)

        # Parse questions JSON
        questions = json.loads(questions_json)

        metadata = {
            "class_grade": class_grade,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "isbn": ""
        }

        result = service.generate_answers(
            chapter_text=chapter_text,
            questions=questions,
            metadata=metadata
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    