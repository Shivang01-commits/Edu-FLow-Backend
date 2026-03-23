import uuid
from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional,List
from decimal import Decimal


class RegisterTeacherRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: date
    designation: str
    salary: Decimal = Field(..., gt=0, description="The employee's salary")
    phone_number: str
    join_date: date


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

class BulkEnrollResponse(BaseModel):
    status: str = Field(..., description="success, validation_failed")
    total_rows: int
    enrolled_count: int
    skipped_count: int
    failed_count: int
    skipped_rows: Optional[List[dict]] = []
    failed_rows: Optional[List[dict]] = []
