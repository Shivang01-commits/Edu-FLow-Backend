from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class RegisterSchoolRequest(BaseModel):
    school_name: str
    admin_email: EmailStr
    school_address: Optional[str] = None
    school_phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    board_affiliation: Optional[str] = None  # "CBSE", "ICSE", "State Board" etc.

    # Step 2 — Admin details
    admin_first_name: str
    admin_last_name: Optional[str] = None
    admin_phone: Optional[str] = None
    admin_date_of_birth: Optional[date] = None
