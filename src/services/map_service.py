import logging
import time
import tiktoken
from src.prompts.prompt_returner import PromptReturner
from src.utils.token_limiter import TokenAwareLimiter
logger = logging.getLogger(__name__)

prompt_returner=PromptReturner()
map_token_limiter=TokenAwareLimiter()
MAX_RETRIES=3
EXPECTED_OUTPUT_TOKEN_MULTIPLIER=1.6

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

            combined_text = "\n\n[New Section]\n\n".join(batch)

            prompt = prompt_returner.get_summary_prompt(subject=subject,doc_type=type,class_level=class_level,context=combined_text,prompt_selector="map",medium=medium)
            
            
            estimated_tokens=self.count_tokens(prompt)*EXPECTED_OUTPUT_TOKEN_MULTIPLIER
            
            for attempts in range(MAX_RETRIES):
                try :

                    #To wait if near Rate limit
                    map_token_limiter.wait_if_needed(estimated_tokens)

                    logger.info(f"Processing batch {batch_num}/{len(batches)}")
                    logger.info(f"Attempt {attempts+1}/{MAX_RETRIES}")

                    response = self.llm.invoke(prompt)
                    summary_text=getattr(response,"content","").strip()

                    if not summary_text:
                        raise ValueError("Empty response from LLM")
                    
                    metadata = getattr(response, "response_metadata", None) or {}
                    usage = metadata.get("token_usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                       

                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)

                    cached_tokens = usage.get("prompt_tokens_details", {}) or {}
                    cached_tokens = cached_tokens.get("cached_tokens", 0)

                    processed_tokens = (prompt_tokens - cached_tokens) + completion_tokens
                    map_token_limiter.update_usage(processed_tokens)

                    break

                except Exception as e:

                    if attempts==MAX_RETRIES-1:
                        raise ValueError("Reattempts exhausted moving to next batch")
                    if "429" in str(e):
                        wait_time=60
                        logger.info(f"429-Rate limit hit. Waiting {wait_time} befire retry..")
                    elif "Empty response" in str(e):
                        wait_time=5
                        logger.info("Empty LLM Response. Retrying...")
                    else:
                        wait_time=10
                        logger.info(f"Temporary error:{e} Retrying...") 
                    time.sleep(wait_time)
            
            if summary_text:
                batch_summaries.append(summary_text)
            
        logger.info(f"Batch summaries generated: {len(batch_summaries)}")

        return batch_summaries
