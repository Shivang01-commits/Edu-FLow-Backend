import uuid
from typing import Optional
from pydantic import BaseModel


class GeneratePresentationRequest(BaseModel):
    class_chapter_id: uuid.UUID
    template: Optional[str] = "general"
    # Available built-in templates:
    # neo-general, neo-modern, neo-standard, neo-swift
    # general, modern, standard, swift
    theme: Optional[str] = "professional-light"
    # Available themes:
    # edge-yellow, light-rose, mint-blue, professional-blue, professional-dark
    export_as: Optional[str] = "pptx"
    language: Optional[str] = "English"
