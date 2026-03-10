import os
from src.rag.pipeline import Pipeline


class IngestionService:

    def __init__(self):
        self.pipeline = Pipeline()

    def ingest_pdf(self, file_path, metadata):

        result = self.pipeline.pipeline(
            file_path=file_path,
            metadata=metadata
        )

        return result