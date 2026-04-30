from src.llms.openai import OpenAILLM
from src.utils.llm_json_parser import LLMJsonParser
from src.prompts.prompt_returner import PromptReturner
from src.utils.pdf_extractor import PDFExtractor
from src.rag.pipeline import Pipeline
import json


class BookIngestionService:
    def __init__(self):
        self.llm = OpenAILLM()
        self.parser = LLMJsonParser(self.llm)
        self.prompts = PromptReturner()
        self.vector_pipeline = Pipeline()

    def ingest_book(self, file_path: str, metadata: dict):

        # Step 1: Extract full chapter text
        chapter_text = PDFExtractor.extract_text(file_path)

        if not chapter_text or len(chapter_text.strip()) == 0:
            raise ValueError("Extracted chapter text is empty")

        # Step 2: Store chunks in vector DB (for RAG later)
        self.vector_pipeline.pipeline(file_path, metadata)

        # Step 3: Generate Summary
        summary = self.generate_summary(chapter_text, metadata)

        # Step 4: Generate Q&A (questions + answers)
        qa_bank = self.extract_questions_answers(chapter_text, metadata)

        # Step 5: Generate Quiz
        quiz = self.generate_quiz(summary, metadata)

        # Step 6: Generate PPT
        ppt = self.generate_ppt(summary, metadata)

        return {
            "scraped_chapter": chapter_text,
            "summary": summary,
            "qa_bank": qa_bank,
            "quiz": quiz,
            "ppt_structure": ppt,
        }

    def generate_summary(self, chapter_text, metadata):

        prompt = self.prompts.get_summary_prompt(
            class_grade=metadata["class_grade"],
            subject=metadata["subject"],
            chapter_title=metadata["chapter_title"],
            chapter_text=chapter_text,
        )

        result = self.parser.invoke_llm_with_retry(
            prompt=prompt, validation_type="summary"
        )

        return {
            "heading": f"Summary of Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "summary": result["summary"],
            "key_points": result["key_points"],
        }

    def extract_questions_answers(self, chapter_text, metadata):

        # Step 1: Extract questions
        prompt = self.prompts.get_exercise_extraction_prompt(
            metadata["class_grade"],
            metadata["subject"],
            metadata["chapter_title"],
            chapter_text,
        )

        extracted_questions = self.parser.invoke_llm_with_retry(
            prompt=prompt, validation_type="exercise_extraction"
        )

        # Step 2: Generate answers (FIXED — removed early return bug)
        answers = self.generate_answers(
            chapter_text=chapter_text, questions=extracted_questions, metadata=metadata
        )

        return {
            "heading": f"Q/A of Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "qa_bank": answers,
        }

    def generate_answers(self, chapter_text, questions: dict, metadata):

        questions_json = json.dumps(questions, ensure_ascii=False)

        prompt = self.prompts.get_exercise_answering_prompt(
            class_grade=metadata["class_grade"],
            subject=metadata["subject"],
            chapter_title=metadata["chapter_title"],
            questions_json=questions_json,
            chapter_text=chapter_text,
        )

        return self.parser.invoke_llm_with_retry(
            prompt=prompt, validation_type="exercise_answering"
        )

    def generate_quiz(self, summary, metadata):

        summary_text = summary["summary"]

        prompt = self.prompts.get_quiz_prompt(
            class_grade=metadata["class_grade"],
            subject=metadata["subject"],
            chapter_title=metadata["chapter_title"],
            chapter_summary=summary_text,
        )

        result = self.parser.invoke_llm_with_retry(
            prompt=prompt, validation_type="quiz"
        )

        return {
            "heading": f"Quiz: Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "quiz": result,
        }

    def generate_ppt(self, summary, metadata):

        summary_text = summary["summary"]

        prompt = self.prompts.get_ppt_prompt(
            class_grade=metadata["class_grade"],
            subject=metadata["subject"],
            chapter_title=metadata["chapter_title"],
            chapter_summary=summary_text,
        )

        result = self.parser.invoke_llm_with_retry(prompt=prompt, validation_type="ppt")

        return {
            "heading": f"PPT of Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "ppt": result,
        }
