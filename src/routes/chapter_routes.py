from fastapi import APIRouter, UploadFile, File, Form
import os

from src.services.ingestion_service import IngestionService
from src.services.summary_service_MR import SummaryService


router = APIRouter(prefix="/chapters", tags=["Chapters"])

UPLOAD_DIR = "data/pdfs"

ingestion_service = IngestionService()
summary_service = SummaryService()


@router.post("/upload")
async def upload_chapter(
    file: UploadFile = File(...),
    class_level: int = Form(...),
    subject: str = Form(...),
    type: str = Form(" "),
    chapter: int = Form(...),
    medium: str = Form("english"),
):
    """
    Teacher uploads a chapter PDF.
    The system stores vectors in Qdrant.
    """

    # ensure directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = f"{UPLOAD_DIR}/{file.filename}"

    # save uploaded PDF
    with open(file_path, "wb") as f:
        f.write(await file.read())

    metadata = {
        "class": class_level,
        "subject": subject.lower().replace(" ", "_"),
        "type": type.lower().replace(" ", "_"),
        "chapter": chapter,
        "medium": medium.lower(),
    }

    result = ingestion_service.ingest_pdf(file_path=file_path, metadata=metadata)

    return {"message": "Chapter uploaded and processed successfully", "result": result}


@router.get("/summary")
def generate_summary(
    class_level: int, subject: str, chapter: int, type: str="", medium: str="english"
):
    """
    Generate summary of a chapter using RAG.
    """

    metadata = {
        "class": class_level,
        "subject": subject,
        "chapter": chapter,
        "type": type,
        "medium": medium,
    }

    summary = summary_service.summarize_chapter_map_reduce(metadata)

    return summary
