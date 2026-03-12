from src.rag.pipeline import Pipeline
from src.llms.groq import GroqLLM
from src.prompts.prompt_manager import PromptManager
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
        self.max_retries = 2
        self.batch_size = 3  # Batch 3 chunks per request
        self.retry_delay = 1  # seconds between retries
        self.map_service = MapService(self.llm, self.batch_size)
        self.reduce_service = ReduceService(self.prompt_manager,self.parser)

    def summarize_chapter_mapreduce(self, metadata):
        """
        Generate a summary using Map-Reduce pattern.
        
        Step 1 (Map): Split chapter into batches and summarize each batch
        Step 2 (Reduce): Combine batch summaries into final summary
        
        This approach:
        - Processes entire chapter (no content loss)
        - Stays within token limits (~3.5K per request)
        - Stays within rate limits (~8-10 requests for average chapter)
        
        Args:
            metadata (dict): Contains class, subject, type, chapter, medium
            
        Returns:
            dict: Summary response with consistent structure
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
                all_chunks, 
                subject, 
                doc_type, 
                class_level, 
                medium
            )
            
            logger.info(f"Generated {len(batch_summaries)} batch summaries")
            
            # Step 3 (REDUCE): Combine batch summaries into final summary
            logger.info("Step 3 (REDUCE): Creating final summary...")
            final_summary = self.reduce_service.generate_final_summary(
                batch_summaries,
                subject,
                doc_type,
                class_level,
                medium
            )
            
            # Step 4: Build response
            result = {
                "class": class_level,
                "subject": subject,
                "chapter": chapter,
                "summary": {
                    "text": final_summary["text"],
                    "key_points": final_summary["key_points"],
                    "takeaway": final_summary["takeaway"]
                }
            }
            
            logger.info("=== Map-Reduce Summary Complete ===")
            return result
            
        except Exception as e:
            logger.error(f"Error in summarize_chapter_mapreduce: {e}")
            return {
                "error": "Failed to generate summary",
                "details": str(e)
            }

    


    def _get_rag_query(self, subject, doc_type):
        """
        Determine the best RAG query based on subject and type.
        """
        subject = subject.lower()
        doc_type = doc_type.lower()
        
        if subject == "mathematics":
            return "formulas, theorems, key concepts, solutions, problem-solving methods, examples"
        
        elif subject == "english" and doc_type == "literature":
            return "chapter summary, key ideas, main concepts, important facts"
        
        elif subject == "english" and doc_type == "grammar":
            return "grammar rules, sentence structure, tenses, examples, usage, corrections"
        
        elif subject == "hindi" and doc_type == "literature":
            return "मुख्य विषय, विचार, पाठ, संदेश, महत्वपूर्ण बातें, उदाहरण"
        
        elif subject == "hindi" and doc_type == "grammar":
            return "व्याकरण नियम, विधि, उदाहरण, संरचना, शब्द, वाक्य"
        
        elif subject == "sanskrit":
            return "मुख्य विषय, श्लोक, पाठ, संदेश, कथानक, महत्वपूर्ण विचार, उदाहरण"
        
        elif subject in ["physics", "chemistry"]:
            return "key concepts, processes, reactions, formulas, laws, important facts, examples"
        
        else:
            return "main concepts, definitions, key points, important facts, examples, explanations"