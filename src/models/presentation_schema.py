from pydantic import BaseModel


class GeneratePresentationRequest(BaseModel):
    template: str = "general"
    theme: str = "professional-dark"
    language: str = "en"
    export_as: str = "pptx"
