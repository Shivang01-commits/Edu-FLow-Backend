import logging
import time
import tiktoken
from src.prompts.prompt_returner import PromptReturner
logger = logging.getLogger(__name__)

prompt_returner=PromptReturner()

class MapService:
    def __init__(self, llm, max_tokens_per_batch=2000):
        self.llm = llm
        self.max_tokens_per_batch = max_tokens_per_batch
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text):
        return len(self.tokenizer.encode(text))

    def summarize_batches(self, chunks, subject, class_level,type,medium):

        batches = []
        current_batch = []
        current_tokens = 0

        # build token-aware batches
        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk)
            
            if current_tokens + chunk_tokens > self.max_tokens_per_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
                
            current_batch.append(chunk)
            current_tokens += chunk_tokens

        if current_batch:
            batches.append(current_batch)

        logger.info(f"Created {len(batches)} batches from {len(chunks)} chunks")

        batch_summaries = []

        for batch_num, batch in enumerate(batches, start=1):
            logger.info(f"Processing batch {batch_num}/{len(batches)}")

            combined_text = "\n\n[New Section]\n\n".join(batch)

            prompt = prompt_returner.get_summary_prompt(subject=subject,doc_type=type,class_level=class_level,context=combined_text,prompt_selector="map",medium=medium)
            
            response = self.llm.invoke(prompt)
            # print(response.response_metadata)


            if not response:
                raise ValueError("LLM returned None response")

            summary_text = getattr(response, "content", "").strip()

            if summary_text:
                batch_summaries.append(summary_text)

            time.sleep(10)
        
        logger.info(f"Batch summaries generated: {len(batch_summaries)}")

        return batch_summaries
