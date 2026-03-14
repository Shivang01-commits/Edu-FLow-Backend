from pydantic import BaseModel


class GenerateSummarySchema(BaseModel):
    class_level: int
    subject: str
    chapter: int

    # optional fields but always string
    type: str = ""
    medium: str = "english"
