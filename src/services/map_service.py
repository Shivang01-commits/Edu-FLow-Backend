import logging
import time

logger = logging.getLogger(__name__)


class MapService:

    def __init__(self, llm, batch_size=3):
        self.llm = llm
        self.batch_size = batch_size

    def summarize_batches(self, chunks, subject, class_level):
        batch_summaries = []

        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1

            total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size
            logger.info(f"Processing batch {batch_num}/{total_batches}")


            combined_text = "\n\n[New Section]\n\n".join(batch)

            prompt = f"""You are a teaching assistant. Summarize the following sections from a {subject} chapter for Class {class_level} students.

Sections to summarize:
{combined_text}

Provide a brief 3-4 sentence summary of all these sections combined.

Return ONLY the summary text, no JSON, no formatting."""

            response = self.llm.invoke(prompt)

            if not response:
                raise ValueError("LLM returned None response")

            summary_text = getattr(response, "content", "").strip()

            if summary_text:
                batch_summaries.append(summary_text)

            time.sleep(0.5)

        return batch_summaries
