import logging
import time
import tiktoken

logger = logging.getLogger(__name__)


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

            prompt = f"""You are a teaching assistant. Summarize the following sections from a {subject} chapter for Class {class_level} students.
            LANGUAGE: Respond in {medium}. Do Not Add new Topics or Concepts which are not in sections below.
            Sections to summarize:
            {combined_text}
            Summarize the section in 4-5 sentences (max 150 words).
            Focus only on key ideas.
            Return ONLY the summary text, no JSON, no formatting."""

            response = self.llm.invoke(prompt)

            if not response:
                raise ValueError("LLM returned None response")

            summary_text = getattr(response, "content", "").strip()

            if summary_text:
                batch_summaries.append(summary_text)

            time.sleep(1.5)
        
        logger.info(f"Batch summaries generated: {len(batch_summaries)}")

        return batch_summaries
