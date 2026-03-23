from pydantic import BaseModel, Field
from typing import Dict, Optional


class SubmitQuizRequest(BaseModel):
    student_answers: Dict[int, Optional[str]] = Field(
        ...,
        description="Student answers as dict: {'1': 'A', '2': 'B', ...}. Use null for unanswered questions.",
    )
