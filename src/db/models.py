import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .main import Base


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class NcertBook(Base):
    __tablename__ = "ncert_books"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_no = Column(Integer, index=True)
    subject = Column(String, index=True)
    chapter = Column(Integer, index=True)
    type = Column(String)
    medium = Column(String)
    content = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint(
            "class_no",
            "subject",
            "chapter",
            "type",
            "medium",
            name="unique_chapter",
        ),
    )
    (Index("chapter_lookup_idx", "class_no", "subject", "chapter"),)
