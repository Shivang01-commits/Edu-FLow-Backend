from typing import List
from pydantic import BaseModel


class StudentAnswer(BaseModel):
    question_number: int
    selected_option: str


class SubmitQuizRequest(BaseModel):
    answers: List[StudentAnswer]
