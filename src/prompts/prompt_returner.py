import os
import logging

logger = logging.getLogger(__name__)


class PromptReturner:
    """
    Manages prompt templates for different features.
    """

    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.supported_languages = ["english", "hindi", "sanskrit"]

    def get_summary_prompt(
        self, subject, doc_type, class_level, context, prompt_selector:str,medium="english"
    ):
        """
        Get summary prompt for students to understand the chapter.
        """
        # Normalize inputs
        subject = subject.lower().strip()
        doc_type = doc_type.lower().strip() if doc_type else ""
        medium = medium.lower().strip() if medium else "english"

        # Combine subject and type if both present
        if doc_type:
            combined_subject = f"{subject}_{doc_type}"
        else:
            combined_subject = subject

        # Get language name
        language = self._get_language(medium)

        # Load prompt file
        if prompt_selector=="reduce":
            prompt_file = os.path.join(self.BASE_DIR, "summary", "reduce_prompt.txt")
        else:
            prompt_file= os.path.join(self.BASE_DIR, "summary", "map_prompt.txt") 

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            logger.info(f"Loaded prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Replace placeholders
        prompt = prompt_template.format(
            subject=combined_subject,
            class_level=class_level,
            language=language,
            context=context,
        )
        return prompt


    def get_quiz_prompt(self, subject, class_level, context, medium="english"):
        pass

    def get_qa_prompt(self, subject, class_level, context, medium="english"):
        pass

    def _get_language(self, medium):
      
        language_map = {
            "english": "English",
            "hindi": "Hindi",
            "sanskrit": "Sanskrit"
        }
        language = language_map.get(medium, "English")
        return language