import uuid
import traceback
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.db.models import Book
from src.utils.presenton_utils import (
    transform_ppt_structure,
    create_presentation_from_json,
    download_pptx_bytes,
)
from src.utils.cloudinary_utils import upload_pptx_to_cloudinary


class PresentationService:
    def initiate_ppt_generation(
        self,
        db: Session,
        book_id: uuid.UUID,
        background_tasks,
        template: str = "default",
        theme: str = "professional-dark",
        language: str = "en",
        export_as: str = "pptx",
    ) -> dict:
        book = db.query(Book).filter(Book.book_id == book_id).first()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if not book.ppt_structure:
            raise HTTPException(
                status_code=400,
                detail="No ppt_structure found on this book. Generate structure first.",
            )

        # Return existing if already ready and not forcing
        if book.ppt_url and book.ppt_status == "ready":
            return {
                "book_id": str(book.book_id),
                "ppt_url": book.ppt_url,
                "ppt_status": book.ppt_status,
                "message": "PPT already generated.",
            }

        # Prevent double-triggering if already in progress
        if book.ppt_status == "generating":
            return {
                "book_id": str(book.book_id),
                "ppt_url": None,
                "ppt_status": "generating",
                "message": "PPT generation already in progress.",
            }

        # Mark as generating
        db.query(Book).filter(Book.book_id == book_id).update(
            {"ppt_status": "generating"}
        )
        db.commit()

        background_tasks.add_task(
            self._generate_ppt_for_book,
            book_id=book_id,
            ppt_structure=book.ppt_structure,
            template=template,
            theme=theme,
            language=language,
            export_as=export_as,
        )

        return {
            "book_id": str(book.book_id),
            "ppt_url": None,
            "ppt_status": "generating",
            "message": "PPT generation started.",
        }

    async def _generate_ppt_for_book(
        self,
        book_id: uuid.UUID,
        ppt_structure: dict,
        template: str,
        theme: str,
        language: str,
        export_as: str,
    ):
        from src.db.main import SessionLocal

        db = SessionLocal()

        VALID_THEMES = ["professional-dark", "mint-blue", "light-rose"]
        if theme not in VALID_THEMES:
            theme = "professional-dark"

        try:
            payload = transform_ppt_structure(
                ppt_structure=ppt_structure,
                template=template,
                theme=theme,
                language=language,
                export_as=export_as,
            )
            import json

            print("🔍 PAYLOAD:", json.dumps(payload, indent=2))  # ADD HERE

            presenton_result = await create_presentation_from_json(payload)

            presenton_result = await create_presentation_from_json(payload)
            pptx_bytes = await download_pptx_bytes(presenton_result["path"])

            cloudinary_result = upload_pptx_to_cloudinary(
                pptx_bytes=pptx_bytes,
                public_id=f"padhai/books/{str(book_id)}/ppt",
            )

            db.query(Book).filter(Book.book_id == book_id).update(
                {
                    "ppt_url": cloudinary_result["url"],
                    "ppt_status": "ready",
                }
            )
            db.commit()

        except Exception:
            traceback.print_exc()
            db.query(Book).filter(Book.book_id == book_id).update(
                {"ppt_status": "failed"}
            )
            db.commit()

        finally:
            db.close()

    def get_ppt_for_book(self, db: Session, book_id: uuid.UUID) -> dict:
        book = db.query(Book).filter(Book.book_id == book_id).first()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        return {
            "book_id": str(book.book_id),
            "ppt_url": book.ppt_url,
            "ppt_status": book.ppt_status,
        }
