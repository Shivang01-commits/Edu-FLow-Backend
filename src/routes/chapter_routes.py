    # import os
    # from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
    # from src.db.main import get_db
    # from sqlalchemy.orm import Session
    # from src.services.ingestion_service import IngestionService
    # from src.services.db_summary_service import DBSummaryService
    # from src.models.chapter_schema import GenerateSummarySchema

    # # TODO: Use this method for authorization of links
    # # from src.core.jwt_handler import get_current_user

    # # !remove this in future
    # router = APIRouter(prefix="/chapters", tags=["Chapters"])

    # # TODO: Use this method for authorization of links
    # # router = APIRouter(prefix="/chapters", tags=["Chapters"], dependencies=Depends(get_current_user))

    # UPLOAD_DIR = "data/pdfs"

    # ingestion_service = IngestionService()
    # db_summary_service = DBSummaryService()


    # @router.post("/upload")
    # async def upload_chapter(
    #     file: UploadFile = File(...),
    #     class_level: int = Form(...),
    #     subject: str = Form(...),
    #     type: str = Form(" "),
    #     chapter: int = Form(...),
    #     medium: str = Form("english"),
    # ):
    #     """
    #     Teacher uploads a chapter PDF.
    #     The system stores vectors in Qdrant.
    #     """

    #     # ensure directory exists
    #     os.makedirs(UPLOAD_DIR, exist_ok=True)

    #     file_path = f"{UPLOAD_DIR}/{file.filename}"

    #     # save uploaded PDF
    #     with open(file_path, "wb") as f:
    #         f.write(await file.read())

    #     metadata = {
    #         "class": class_level,
    #         "subject": subject.lower().replace(" ", "_"),
    #         "type": type.lower().replace(" ", "_"),
    #         "chapter": chapter,
    #         "medium": medium.lower(),
    #     }

    #     result = ingestion_service.ingest_pdf(file_path=file_path, metadata=metadata)

    #     return {"message": "Chapter uploaded and processed successfully", "result": result}


    # @router.post("/generate-summary", status_code=201)
    # def generate_summary(
    #     data: GenerateSummarySchema,
    #     db: Session = Depends(get_db),
    # ):

    #     metadata = {
    #         "class": data.class_level,
    #         "subject": data.subject.lower().replace(" ", "_"),
    #         "chapter": data.chapter,
    #         "type": data.type,
    #         "medium": data.medium,
    #     }

    #     existing = db_summary_service.get_summary(db, metadata)

    #     if existing:
    #         return existing.content

    #     # summary = summary_service.summarize_chapter_map_reduce(metadata)

    # # if not summary or "error" in summary:
    #         raise HTTPException(status_code=500, detail="Summary generation failed")

    # #  db_summary_service.save_summary(db, metadata, summary)

    # # return summary


    # @router.get("/summary")
    # def get_summary(
    #     class_level: int,
    #     subject: str,
    #     chapter: int,
    #     type: str = "",
    #     medium: str = "english",
    #     db: Session = Depends(get_db),
    # ):

    #     metadata = {
    #         "class": class_level,
    #         "subject": subject,
    #         "chapter": chapter,
    #         "type": type,
    #         "medium": medium,
    #     }

    #     summary = db_summary_service.get_summary(db, metadata)

    #     if not summary:
    #         raise HTTPException(status_code=404, detail="Summary not found")

    #     return summary.content
