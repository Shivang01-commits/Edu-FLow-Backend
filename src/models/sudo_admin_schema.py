from pydantic import BaseModel, EmailStr
import uuid
from datetime import date
from typing import Optional


class CreateSchoolRequest(BaseModel):
    school_name: str
    admin_email: EmailStr
    school_address: Optional[str] = None
    school_phone: Optional[str] = None


class CreateAdminRequest(BaseModel):
    school_id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: date
