import logging

logger = logging.getLogger(__name__)


class ReduceService:

    def __init__(self, prompt_manager, parser):
        self.prompt_manager = prompt_manager
        self.parser = parser

    def generate_final_summary(
        self,
        batch_summaries,
        subject,
        doc_type,
        class_level,
        medium,
    ):
        logger.info("Combining batch summaries into final summary...")

        combined_summaries = "\n\n".join(batch_summaries)

        final_prompt = self.prompt_manager.get_summary_prompt(
            subject=subject,
            doc_type=doc_type,
            class_level=class_level,
            context=combined_summaries,
            medium=medium,
        )

        summary_data = self.parser.invoke_llm_with_retry(final_prompt)

        return summary_data
