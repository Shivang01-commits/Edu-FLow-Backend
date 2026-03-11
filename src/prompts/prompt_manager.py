import os

class PromptManager:
    """
    Manages prompt loading and template filling based on subject and document type.
    Selects appropriate prompt (strict vs mixed) and fills placeholders.
    Includes fallback handling for unknown subjects and languages.
    """
    
    def __init__(self):
        # Subjects that require STRICT context-only approach
        # These subjects need exact information from the chapter, no LLM knowledge
        
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.strict_subjects = [
            "english_literature",
            "hindi_literature", 
            "history",
            "social_science"
        ]
        
        # Subjects that can use MIXED approach (context + LLM knowledge)
        # These subjects benefit from explanations and clarifications
        self.mixed_subjects = [
            "mathematics",
            "physics",
            "chemistry",
            "english_grammar",
            "hindi_grammar"
        ]
        
        # Supported languages
        self.supported_languages = ["english", "hindi", "sanskrit"]
    
    def get_summary_prompt(self, subject, doc_type, class_level, context, medium="english"):
        """
        Get the appropriate summary prompt based on subject and type.
        
        Args:
            subject (str): Subject name (e.g., "english", "hindi", "mathematics")
            doc_type (str): Document type (e.g., "literature", "grammar")
            class_level (int): Class/grade level
            context (str): The chapter content from RAG
            medium (str): Language medium (e.g., "english", "hindi", "sanskrit")
                         Default: "english"
        
        Returns:
            str: Complete prompt with all placeholders filled
            
        Raises:
            FileNotFoundError: If prompt file cannot be found
        """
        subject = subject.lower().strip()
        doc_type = doc_type.lower().strip() if doc_type else ""
        medium = medium.lower().strip() if medium else "english"
        
        # Combine subject and type for matching
        # e.g., "english" + "literature" = "english_literature"
        if doc_type:
            combined_subject = f"{subject}_{doc_type}"
        else:
            combined_subject = subject
        
        # Determine which prompt file to use (strict vs mixed)
        # Fallback to mixed for unknown subjects


        if combined_subject in self.strict_subjects:
            prompt_filename = "strict_prompt.txt"
        else:
            # Default to mixed for unknown subjects (safer approach)
            prompt_filename = "mixed_prompt.txt"
        
        # Build absolute path to prompt file
        # This works regardless of where Flask app is run from

        prompt_file = os.path.join(self.BASE_DIR, "summary", prompt_filename)
      
        # Validate and get language
        # Fallback to English for unknown languages
        if medium not in self.supported_languages:
            language = "English"
        else:
            language = medium.capitalize()  # "hindi" → "Hindi", "english" → "English"
        
        # Load prompt from file
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        # Fill all placeholders in the template
        prompt = prompt_template.format(
            subject=combined_subject,
            class_level=class_level,
            language=language,
            context=context
        )
       
        return prompt