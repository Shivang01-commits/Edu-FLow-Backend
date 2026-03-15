import os
import logging

logger = logging.getLogger(__name__)


class PromptReturner:
    """
    Manages prompt templates for different features.
    """

    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    def get_summary_prompt(
        self, class_grade:int,subject:str,chapter_title:str,chapter_text
    ):
        """
        Get summary prompt for students to understand the chapter.
        """
        # Normalize inputs
        subject = subject.lower().strip()

        prompt_file= os.path.join(self.BASE_DIR,"summary_prompt.txt") 

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            logger.info(f"Loaded prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Replace placeholders
        prompt = prompt_template.format(
            chapter_text=chapter_text,
            class_grade=class_grade,
            subject=subject,
            chapter_title=chapter_title
        )
        return prompt

    def get_quiz_prompt(
        self, class_grade:int,subject:str,chapter_title:str,chapter_summary
    ):
        """
        Get quiz prompt for students to understand the chapter.
        """
        # Normalize inputs
        subject = subject.lower().strip()

        prompt_file= os.path.join(self.BASE_DIR,"quiz_prompt.txt") 

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            logger.info(f"Loaded prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Replace placeholders
        prompt = prompt_template.format(
            chapter_summary=chapter_summary,
            class_grade=class_grade,
            subject=subject,
            chapter_title=chapter_title
        )
        return prompt


    def get_ppt_prompt(
        self, class_grade:int,subject:str,chapter_title:str,chapter_summary
    ):
        """
        Get ppt prompt for students to understand the chapter.
        """
        # Normalize inputs
        subject = subject.lower().strip()

        prompt_file= os.path.join(self.BASE_DIR,"ppt_prompt.txt") 

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            logger.info(f"Loaded prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Replace placeholders
        prompt = prompt_template.format(
            chapter_summary=chapter_summary,
            class_grade=class_grade,
            subject=subject,
            chapter_title=chapter_title
        )
        return prompt


    def get_exercise_extraction_prompt(
        self, class_grade:int,subject:str,chapter_title:str,chapter_text
    ):
        """
        Get back excercise extraction prompt for students to understand the chapter.
        """
        # Normalize inputs
        subject = subject.lower().strip()

        prompt_file= os.path.join(self.BASE_DIR,"exercise_extraction_prompt.txt") 

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            logger.info(f"Loaded prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Replace placeholders
        prompt = prompt_template.format(
            chapter_text=chapter_text,
            class_grade=class_grade,
            subject=subject,
            chapter_title=chapter_title
        )
        return prompt
    

    def get_exercise_answering_prompt(
        self, class_grade:int,subject:str,chapter_title:str,chapter_text,questions_json
    ):
        """
        Get back excersise answering  prompt for students to understand the chapter.
        """
        # Normalize inputs
        subject = subject.lower().strip()

        prompt_file= os.path.join(self.BASE_DIR,"exercise_answering_prompt.txt") 

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            logger.info(f"Loaded prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Replace placeholders
        prompt = prompt_template.format(
            chapter_text=chapter_text,
            extracted_questions_json=questions_json,
            class_grade=class_grade,
            subject=subject,
            chapter_title=chapter_title
        )
        return prompt

