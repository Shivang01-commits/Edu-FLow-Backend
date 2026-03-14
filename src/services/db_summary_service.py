from sqlalchemy.orm import Session
from src.db.models import NcertBook


class DBSummaryService:
    def save_summary(self, db: Session, metadata: dict, summary: dict):
        record = NcertBook(
            class_no=metadata["class"],
            subject=metadata["subject"],
            chapter=metadata["chapter"],
            type=metadata.get("type"),
            medium=metadata.get("medium"),
            content=summary,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    def get_summary(self, db: Session, metadata: dict):
        return (
            db.query(NcertBook)
            .filter(
                NcertBook.class_no == metadata["class"],
                NcertBook.subject == metadata["subject"],
                NcertBook.chapter == metadata["chapter"],
            )
            .first()
        )
