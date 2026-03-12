import logging

logger = logging.getLogger(__name__)


class ReduceService:
    def __init__(self, prompt_manager, parser):
        self.prompt_manager = prompt_manager
        self.parser = parser

    def combine_summaries(self, summaries, subject, class_level):
        """
        Combine multiple summaries into a shorter intermediate summary.
        Used for hierarchical reduction.
        """

        combined = "\n\n".join(summaries)

        prompt = f"""
    You are helping summarize a {subject} chapter for Class {class_level} students.

    Below are partial summaries of different sections of the chapter.

    {combined}

    Write a concise combined summary (5–6 sentences) that captures the main ideas.
    Return ONLY the summary text.
    """

        response = self.parser.llm.invoke(prompt)

        if not response:
            raise ValueError("LLM returned None response")

        return getattr(response, "content", "").strip()

    def hierarchical_reduce(
        self,
        batch_summaries,
        subject,
        doc_type,
        class_level,
        medium,
    ):
        """
        Perform hierarchical MapReduce if summaries are too many.
        """

        # If summaries are small, skip hierarchy
        if len(batch_summaries) <= 6:
            return self.generate_final_summary(
                batch_summaries,
                subject,
                doc_type,
                class_level,
                medium,
            )

        logger.info("Running hierarchical reduction...")

        grouped = []
        group_size = 4

        for i in range(0, len(batch_summaries), group_size):
            group = batch_summaries[i : i + group_size]

            combined = self.combine_summaries(
                group,
                subject,
                class_level,
            )

            grouped.append(combined)

        # Now generate final structured summary
        return self.generate_final_summary(
            grouped,
            subject,
            doc_type,
            class_level,
            medium,
        )

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
