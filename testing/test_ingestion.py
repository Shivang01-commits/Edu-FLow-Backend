from src.services.ingestion_service import IngestionService

service = IngestionService()

# metadata given by user by formdata
metadata = {"class": 7, "subject": "science", "chapter": 5}

result = service.ingest_pdf(file_path="data/pdfs/gecu105.pdf", metadata=metadata)

print(result)
