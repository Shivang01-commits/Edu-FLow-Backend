import uuid
import traceback
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.db.models import Book
from src.utils.presenton_utils import (
    transform_ppt_structure,
    create_presentation_from_json,
    download_pptx_bytes,
)
from src.utils.cloudinary_utils import upload_pptx_to_cloudinary


class PresentationService:
    async def initiate_ppt_generation(
        self,
        db: AsyncSession,
        book_id: uuid.UUID,
        background_tasks,
        template: str = "general",
        theme: str = "professional-dark",
        language: str = "en",
        export_as: str = "pptx",
    ):
        result = await db.execute(select(Book).where(Book.book_id == book_id))
        book = result.scalar_one_or_none()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if not book.ppt_structure:
            raise HTTPException(
                status_code=400,
                detail="No ppt_structure found. Run ingestion first.",
            )

        if book.ppt_status == "generating":
            return {
                "book_id": str(book.book_id),
                "ppt_status": "generating",
                "message": "Already generating",
            }

        if book.ppt_status == "ready":
            return {
                "book_id": str(book.book_id),
                "ppt_url": book.ppt_url,
                "ppt_status": "ready",
            }

        # ✅ mark generating
        await db.execute(
            update(Book).where(Book.book_id == book_id).values(ppt_status="generating")
        )
        await db.commit()

        # ✅ background
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
            "ppt_status": "generating",
            "message": "PPT generation started",
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
        from src.db.main import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            try:
                payload = transform_ppt_structure(
                    ppt_structure=ppt_structure,
                    template=template,
                    theme=theme,
                    language=language,
                    export_as=export_as,
                )

                presenton_result = await create_presentation_from_json(payload)
                pptx_bytes = await download_pptx_bytes(presenton_result["path"])

                cloudinary_result = upload_pptx_to_cloudinary(
                    pptx_bytes=pptx_bytes,
                    public_id=f"padhai/books/{str(book_id)}/ppt",
                )

                await db.execute(
                    update(Book)
                    .where(Book.book_id == book_id)
                    .values(
                        ppt_url=cloudinary_result["url"],
                        ppt_status="ready",
                    )
                )
                await db.commit()

            except Exception as e:
                print("❌ PPT FAILED:", e)

                await db.execute(
                    update(Book)
                    .where(Book.book_id == book_id)
                    .values(ppt_status="failed")
                )
                await db.commit()

    async def get_ppt_for_book(self, db: AsyncSession, book_id: uuid.UUID) -> dict:
        result = await db.execute(select(Book).where(Book.book_id == book_id))
        book = result.scalar_one_or_none()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        return {
            "book_id": str(book.book_id),
            "ppt_url": book.ppt_url,
            "ppt_status": book.ppt_status,
        }
