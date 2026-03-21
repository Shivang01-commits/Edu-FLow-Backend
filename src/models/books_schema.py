from pydantic import BaseModel, Field
from typing import Optional, Literal
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


class GetChapterContentRequest(BaseModel):
    book_name: str = Field(
        ..., min_length=1, description="Name of the book"
    )  # Dropdown
    class_grade: int = Field(
        ..., ge=1, le=12, description="Class grade (1-12)"
    )  # Autofill
    subject: str = Field(..., min_length=1, description="Subject name")  # Autofill
    chapter_number: int = Field(
        ..., ge=1, description="Chapter number"
    )  # Teacher will fill
    content_type: Literal["summary", "quiz", "qa_bank", "ppt_structure"] = (
        Field(  # AutoFill
            ..., description="Type of content to fetch"
        )
    )


class EditChapterContentRequest(BaseModel):
    class_id: uuid.UUID = Field(..., description="The class ID")
    book_name: str = Field(..., description="Book name")
    class_grade: int = Field(..., description="Class grade")
    subject: str = Field(..., description="Subject")
    chapter_number: str = Field(..., description="Chapter number")
    # chapter_title: str = Field(..., description="Chapter title")
    content_type: Literal["summary", "quiz", "qa_bank", "ppt_structure"] = Field(
        ..., description="Type of content to edit"
    )
