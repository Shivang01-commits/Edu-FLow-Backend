from src.rag.pipeline import Pipeline
from src.llms.groq import GroqLLM
from src.prompts.prompt_manager import PromptManager
from src.prompts.prompt_returner import PromptReturner
import logging
import time
from src.utils.llm_json_parser import LLMJsonParser
from src.services.map_service import MapService
from src.services.reduce_service import ReduceService


logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(self):
        self.rag = Pipeline()
        self.llm = GroqLLM().get_llm()
        self.parser = LLMJsonParser(self.llm)
        self.prompt_manager = PromptManager()
        self.prompt_returner=PromptReturner()
        self.max_retries = 2
        self.batch_size = 3  # Batch 3 chunks per request
        self.retry_delay = 1  # seconds between retries
        self.map_service = MapService(self.llm)
        self.reduce_service = ReduceService(self.prompt_returner, self.parser)

    def summarize_chapter_map_reduce(self, metadata):
        """
        Generate a summary using Map-Reduce pattern.

        Step 1 (Map): Split chapter into batches and summarize each batch
        Step 2 (Reduce): Combine batch summaries into final summary
        """
        try:
            logger.info("=== Starting Map-Reduce Summary ===")

            # Extract metadata
            class_level = metadata.get("class")
            subject = metadata.get("subject", "").lower()
            doc_type = metadata.get("type", "").lower()
            chapter = metadata.get("chapter")
            medium = metadata.get("medium", "english").lower()

            # Step 1: Get ALL chunks from the chapter (sequential, not similarity search)
            logger.info("Step 1: Retrieving all chunks from chapter...")
            all_chunks = self.rag.get_all_chunks(metadata)

            if not all_chunks:
                raise ValueError("No chunks retrieved from chapter")

            logger.info(f"Retrieved {len(all_chunks)} total chunks")

            # Step 2 (MAP): Summarize chunks in batches
            logger.info("Step 2 (MAP): Summarizing chunks in batches...")
            batch_summaries = self.map_service.summarize_batches(
                chunks=all_chunks,subject= subject, type=doc_type, class_level=class_level, medium=medium
            )

            logger.info(f"Generated {len(batch_summaries)} batch summaries")

            # Step 3 (REDUCE): Combine batch summaries into final summary
            logger.info("Step 3 (REDUCE): Creating final summary...")
            final_summary = self.reduce_service.hierarchical_reduce(
                batch_summaries, subject, doc_type, class_level, medium
            )

            # Step 4: Build response
            result = {
                "class": class_level,
                "subject": subject,
                "chapter": chapter,
                "summary": {
                    "text": final_summary["text"],
                    "key_points": final_summary["key_points"],
                    "takeaway": final_summary["takeaway"],
                },
            }

            logger.info("=== Map-Reduce Summary Complete ===")
            return result

        except Exception as e:
            logger.error(f"Error in summarize_chapter_mapreduce: {e}")
            return {"error": "Failed to generate summary", "details": str(e)}
