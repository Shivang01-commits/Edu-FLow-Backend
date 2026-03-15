from src.llms.openai import OpenAILLM
from src.utils.llm_json_parser import LLMJsonParser
from src.prompts.prompt_returner import PromptReturner
from src.utils.pdf_extractor import PDFExtractor
from src.rag.pipeline import Pipeline


class BookIngestionService:

    def __init__(self):

        self.llm = OpenAILLM()
        self.parser = LLMJsonParser(self.llm)
        self.prompts = PromptReturner()
        self.vector_pipeline = Pipeline()

    def ingest_book(self, file_path: str, metadata: dict):

        # Step 1: Extract full chapter text
        chapter_text = PDFExtractor.extract_text(file_path)

        # Step 2: Store chunks in vector DB (for RAG later)
        self.vector_pipeline.pipeline(file_path, metadata)

        # Step 3: Generate Summary
        summary = self.generate_summary(chapter_text, metadata)

        # Step 4: Extract Questions
        questions = self.extract_questions_answers(chapter_text, metadata)

        # Step 5: Answer Questions
        qa_bank = self.generate_answers(chapter_text, questions, metadata)

        # Step 6: Generate Quiz 
        quiz = self.generate_quiz(summary, metadata)
    
        # Step 7: Generate PPT
        ppt = self.generate_ppt(summary, metadata)

        return {
            "summary": summary,
            "qa_bank": qa_bank,
            "quiz": quiz,
            "ppt_structure": ppt
        }

    def generate_summary(self, chapter_text, metadata):
        
        class_grade=metadata['class_grade']
        subject=metadata['subject']
        chapter_title=metadata['chapter_title']
        isbn=metadata['isbn']

        prompt = self.prompts.get_summary_prompt(class_grade=class_grade,subject=subject,chapter_title=chapter_title,chapter_text=chapter_text
        )

        result= self.parser.invoke_llm_with_retry(prompt=prompt,validation_type="summary")

        return {
            "heading": f"Summary of Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "summary": result
        }

    def extract_questions_answers(self, chapter_text, metadata):

        class_grade=metadata['class_grade']
        subject=metadata['subject']
        chapter_title=metadata['chapter_title']
        isbn=metadata['isbn']
        
        prompt = self.prompts.get_exercise_extraction_prompt(class_grade,subject,chapter_title,chapter_text
        )
        extracted_questions_json= self.parser.invoke_llm_with_retry(prompt=prompt,validation_type="exercise_extraction")

        result=self.generate_answers(chapter_text=chapter_text,questions=extracted_questions_json,metadata=metadata)

        return {
            "heading": f"Q/A of Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "qa_bank": result
        }        

    def generate_answers(self, chapter_text, questions, metadata):

        class_grade=metadata['class_grade']
        subject=metadata['subject']
        chapter_title=metadata['chapter_title']
        isbn=metadata['isbn']

        prompt = self.prompts.get_exercise_answering_prompt(class_grade=class_grade,subject=subject,chapter_title=chapter_title,questions_json=questions,chapter_text=chapter_text
        )

        return self.parser.invoke_llm_with_retry(prompt=prompt,validation_type="exercise_answering")

    def generate_quiz(self, summary, metadata):

        class_grade=metadata['class_grade']
        subject=metadata['subject']
        chapter_title=metadata['chapter_title']
        isbn=metadata['isbn']

        prompt = self.prompts.get_quiz_prompt(class_grade=class_grade,subject=subject,chapter_title=chapter_title,chapter_summary=summary
        )

        result = self.parser.invoke_llm_with_retry(prompt=prompt,validation_type="quiz")

        return {
            "heading": f"Quiz: {metadata['chapter_number']}: {metadata['chapter_title']}",
            "quiz": result
        }
    
    def generate_ppt(self, summary, metadata):

        class_grade=metadata['class_grade']
        subject=metadata['subject']
        chapter_title=metadata['chapter_title']
        isbn=metadata['isbn']

        prompt = self.prompts.get_ppt_prompt(class_grade=class_grade,subject=subject,chapter_title=chapter_title,chapter_summary=summary
        )

        result = self.parser.invoke_llm_with_retry(prompt,validation_type="ppt")

        return {
            "heading": f"PPT of Chapter {metadata['chapter_number']}: {metadata['chapter_title']}",
            "ppt": result
        }        