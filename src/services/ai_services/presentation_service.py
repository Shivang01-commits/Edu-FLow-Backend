import uuid
import traceback

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from src.db.models import Presentation, ClassChapter
from src.models.presentation_schema import GeneratePresentationRequest
from src.utils.presenton_utils import (
    transform_ppt_structure,
    create_presentation_from_json,
    download_pptx_bytes,
    get_template_layouts,
)
from src.utils.cloudinary_utils import upload_pptx_to_cloudinary


class PresentationService:
    def _resolve_ppt_structure(self, class_chapter: ClassChapter) -> dict:
        if class_chapter.is_ppt_overridden and class_chapter.custom_ppt_structure:
            return class_chapter.custom_ppt_structure

        if class_chapter.book and class_chapter.book.ppt_structure:
            return class_chapter.book.ppt_structure

        return None

    def initiate_generation(
        self,
        db: Session,
        current_user,
        data: GeneratePresentationRequest,
        background_tasks: BackgroundTasks,
    ) -> dict:
        class_chapter = (
            db.query(ClassChapter)
            .filter(ClassChapter.class_chapter_id == data.class_chapter_id)
            .first()
        )

        if not class_chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        if class_chapter.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your chapter")

        ppt_structure = self._resolve_ppt_structure(class_chapter)

        if not ppt_structure:
            raise HTTPException(
                status_code=400,
                detail="No PPT structure found. Ask sudo_admin to generate it first.",
            )

        title = ppt_structure.get("heading", "Presentation")

        presentation = Presentation(
            presentation_id=uuid.uuid4(),
            school_id=class_chapter.school_id,
            created_by=current_user.user_id,
            class_chapter_id=class_chapter.class_chapter_id,
            title=title,
            template=data.template,
            theme=data.theme,
            status="generating",
        )
        db.add(presentation)
        db.commit()
        db.refresh(presentation)

        background_tasks.add_task(
            self._run_generation,
            presentation_id=presentation.presentation_id,
            ppt_structure=ppt_structure,
            school_id=str(class_chapter.school_id),
            template=data.template,
            theme=data.theme,
            language=data.language,
            export_as=data.export_as,
        )

        return {
            "presentation_id": str(presentation.presentation_id),
            "status": "generating",
            "message": "Generation started. Poll GET /teacher/presentations/{presentation_id} for status.",
        }

    async def _run_generation(
        self,
        presentation_id: uuid.UUID,
        ppt_structure: dict,
        school_id: str,
        template: str,
        theme: str,
        language: str,
        export_as: str,
    ):
        from src.db.main import SessionLocal

        db = SessionLocal()

        VALID_THEMES = [
            "professional-dark",
            "mint-blue",
            "light-rose",
        ]

        if theme not in VALID_THEMES:
            theme = "professional-blue"

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
                public_id=f"padhai/{school_id}/presentations/{str(presentation_id)}",
            )

            db.query(Presentation).filter(
                Presentation.presentation_id == presentation_id
            ).update(
                {
                    "presenton_id": presenton_result["presentation_id"],
                    "presenton_edit_url": presenton_result["edit_path"],
                    "cloudinary_url": cloudinary_result["url"],
                    "cloudinary_public_id": cloudinary_result["public_id"],
                    "status": "ready",
                }
            )
            db.commit()

        except Exception as e:
            traceback.print_exc()

            if hasattr(e, "response"):
                print("🔥 PRESENTON ERROR:", e.response.text)

            db.query(Presentation).filter(
                Presentation.presentation_id == presentation_id
            ).update({"status": "failed"})
            db.commit()

        finally:
            db.close()

    def get_status(
        self,
        db: Session,
        current_user,
        presentation_id: uuid.UUID,
    ) -> dict:
        presentation = (
            db.query(Presentation)
            .filter(
                Presentation.presentation_id == presentation_id,
                Presentation.created_by == current_user.user_id,
            )
            .first()
        )

        if not presentation:
            raise HTTPException(status_code=404, detail="Presentation not found")

        return {
            "presentation_id": str(presentation.presentation_id),
            "title": presentation.title,
            "status": presentation.status,
            "cloudinary_url": presentation.cloudinary_url,
            "presenton_edit_url": presentation.presenton_edit_url,
            "template": presentation.template,
            "theme": presentation.theme,
            "created_at": str(presentation.created_at),
        }

    def get_all(
        self,
        db: Session,
        current_user,
        class_chapter_id: uuid.UUID = None,
    ) -> list:
        query = db.query(Presentation).filter(
            Presentation.created_by == current_user.user_id,
            Presentation.school_id == current_user.school_id,
        )

        if class_chapter_id:
            query = query.filter(Presentation.class_chapter_id == class_chapter_id)

        presentations = query.order_by(Presentation.created_at.desc()).all()

        return [
            {
                "presentation_id": str(p.presentation_id),
                "title": p.title,
                "status": p.status,
                "cloudinary_url": p.cloudinary_url,
                "presenton_edit_url": p.presenton_edit_url,
                "template": p.template,
                "theme": p.theme,
                "created_at": str(p.created_at),
            }
            for p in presentations
        ]

    async def inspect_template(self, template_id: str) -> dict:
        return await get_template_layouts(template_id)
