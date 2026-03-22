import uuid
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class RegisterTeacherRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: date


class RegisterStudentRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: date
    class_grade: int
    section: str
    admission_number: int
    parent_name: str
    parent_phone: str


class CreateClassRequest(BaseModel):
    grade_level: int
    section: Optional[str] = None


class AssignTeacherRequest(BaseModel):
    teacher_id: uuid.UUID
    subject: Optional[str] = None
    is_classroom_teacher: bool = False
