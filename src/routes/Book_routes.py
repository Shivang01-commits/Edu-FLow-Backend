from fastapi import APIRouter, UploadFile, File, Form
import shutil
import uuid
from src.services.book_ingestion_services import BookIngestionService

router = APIRouter()

service = BookIngestionService()


@router.post("/ingest-book")
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