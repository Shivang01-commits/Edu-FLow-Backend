from pydantic import BaseModel
from typing import Optional
import uuid


class CreateBookRequest(BaseModel):
    book_name: str
    class_grade: int
    subject: str
    chapter_number: int
    chapter_title: str
    scraped_chapter: str
    summary: dict
    qa_bank: dict
    quiz: dict
    ppt_structure: dict
    isbn: Optional[str] = None
    board: str


class UpdateBookFieldsRequest(BaseModel):
    summary: Optional[dict] = None
    qa_bank: Optional[dict] = None
    quiz: Optional[dict] = None
    ppt_structure: Optional[dict] = None
    chapter_title: Optional[str] = None
    scraped_chapter: Optional[str] = None
    isbn: Optional[str] = None


class AssignChapterRequest(BaseModel):
    book_id: uuid.UUID
    teacher_id: uuid.UUID
    chapter_title: str
    subject: str


class OverrideSummaryRequest(BaseModel):
    summary: dict


class OverrideQABankRequest(BaseModel):
    qa_bank: dict


class OverrideQuizRequest(BaseModel):
    quiz: dict


class OverridePPTRequest(BaseModel):
    ppt_structure: dict


class ResetOverridesRequest(BaseModel):
    fields: list[str]
