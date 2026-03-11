from services.summary_service import SummaryService

service = SummaryService()

summary = service.summarize_chapter(
    metadata={"class": 7, "subject": "science", "chapter": 5}
)

print(summary)
