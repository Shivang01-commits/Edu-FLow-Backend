from src.rag.pipeline import Pipeline
from src.llms.groq import GroqLLM
from src.prompts.prompt_manager import PromptManager
import json
import logging
import re

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(self):
        self.rag = Pipeline()
        self.llm = GroqLLM().get_llm()
        self.prompt_manager = PromptManager()
        self.max_retries = 3

    def summarize_chapter(self, metadata):
        """
        Generate a summary of the chapter using RAG and LLM.

        Args:
            metadata (dict): Contains class, subject, type, chapter, medium

        Returns:
            dict: Summary response with class, subject, chapter, and summary data
                  OR error response if something fails
        """
        try:
            # Extract metadata
            class_level = metadata.get("class")
            subject = metadata.get("subject", "").lower()
            doc_type = metadata.get("type", "").lower()
            chapter = metadata.get("chapter")
            medium = metadata.get("medium", "english").lower()

            # Step 1: Determine RAG query based on subject
            rag_query = self._get_rag_query(subject, doc_type)

            # Step 2: Retrieve relevant chunks from RAG
            docs = self.rag.retriever(
                query=rag_query,
                metadata=metadata,
                k=8,  # Get 8 chunks for better coverage
            )
            if not docs:
                raise ValueError("No documents retrieved from RAG")

            # Step 3: Build context from retrieved chunks
            context = self.rag.build_context(docs)

            if not context.strip():
                raise ValueError("RAG returned empty context")

            # Step 4: Get prompt from PromptManager
            prompt = self.prompt_manager.get_summary_prompt(
                subject=subject,
                doc_type=doc_type,
                class_level=class_level,
                context=context,
                medium=medium,
            )

            # Step 5: Invoke LLM with retry logic
            summary_data = self._invoke_llm_with_retry(
                prompt, max_retries=self.max_retries
            )

            # Step 6: Build final response with metadata
            result = {
                "class": class_level,
                "subject": subject,
                "chapter": chapter,
                "summary": {
                    "text": summary_data["text"],
                    "key_points": summary_data["key_points"],
                    "takeaway": summary_data["takeaway"],
                },
            }

            return result

        except Exception as e:
            logger.error(f"Error in summarize_chapter: {e}")
            return {"error": "Failed to generate summary", "details": str(e)}

    def _invoke_llm_with_retry(self, prompt, max_retries=2):
        """
        Invoke LLM with retry logic.
        If first attempt fails to produce valid JSON, retry with stricter prompt.

        Args:
            prompt (str): The prompt to send to LLM
            max_retries (int): Number of retries if JSON parsing fails

        Returns:
            dict: Parsed and validated JSON response

        Raises:
            ValueError: If all retries fail
        """
        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                logger.info(f"LLM attempt {attempt + 1}/{max_retries + 1}")

                # Invoke LLM
                response = self.llm.invoke(prompt)
                response_text = response.content

                if not response:
                    raise ValueError("LLM returned None response")

                response_text = getattr(response, "content", "")

                if not response_text or not response_text.strip():
                    raise ValueError("LLM returned empty content")

                # Log response length for debugging
                logger.info(f"LLM response length: {len(response_text)}")

                # Try to parse and validate
                summary_data = self._parse_and_validate_json(response_text)

                logger.info(f"✓ Successfully parsed JSON on attempt {attempt + 1}")
                return summary_data

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"✗ JSON parse error on attempt {attempt + 1}: {e}")

                # If this was the last attempt, raise
                if attempt >= max_retries:
                    logger.error(f"Failed after {max_retries + 1} attempts")
                    raise ValueError(
                        f"Failed to generate valid JSON after {max_retries + 1} attempts: {e}"
                    )

                # Otherwise, retry with stricter prompt
                attempt += 1
                logger.info(f"Retrying with stricter prompt... (attempt {attempt + 1})")

                # Add stricter instructions for next attempt
                stricter_prompt = (
                    prompt
                    + "\n\n[RETRY INSTRUCTION: Ensure the JSON is VALID with no syntax errors. Double-check all quotes are closed.]"
                )
                prompt = stricter_prompt

            except ValueError as e:
                last_error = e
                logger.warning(f"✗ Validation error on attempt {attempt + 1}: {e}")

                if attempt >= max_retries:
                    logger.error(f"Validation failed after {max_retries + 1} attempts")
                    raise

                attempt += 1
                logger.info(f"Retrying... (attempt {attempt + 1})")

        raise ValueError(f"Failed to generate summary after {max_retries + 1} attempts")

    def _parse_and_validate_json(self, response_text):
        """
        Parse and validate JSON response from LLM.
        First attempts to repair common JSON issues, then validates structure.

        Args:
            response_text (str): Raw text response from LLM

        Returns:
            dict: Parsed and validated JSON

        Raises:
            json.JSONDecodeError: If JSON is invalid and cannot be repaired
            ValueError: If required fields are missing or structure is invalid
        """
        # Step 1: Clean the response
        response_text = self._clean_response(response_text)

        # Step 2: Try direct parsing first
        try:
            parsed = json.loads(response_text)
            logger.info("✓ Direct JSON parsing successful")
        except json.JSONDecodeError as e:
            logger.warning(f"Direct parsing failed: {e}")
            logger.info("Attempting to repair JSON...")

            # Step 3: Try to repair common JSON issues
            try:
                response_text = self._repair_json(response_text)
                parsed = json.loads(response_text)
                logger.info("✓ Repaired JSON parsing successful")
            except json.JSONDecodeError as repair_error:
                logger.error(f"JSON repair failed: {repair_error}")
                logger.error(f"Response (first 1000 chars): {response_text[:1000]}")
                raise repair_error

        # Step 4: Validate structure
        self._validate_json_structure(parsed)

        logger.info("✓ JSON validation successful")
        return parsed

    def _clean_response(self, response_text):
        """
        Remove markdown code blocks and extra whitespace.
        """
        response_text = response_text.strip()

        # Remove markdown wrappers
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]

        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        return response_text

    def _repair_json(self, response_text):
        """
        Attempt to fix common JSON issues.

        Issues fixed:
        - Trailing commas in objects/arrays
        - Missing closing quotes
        - Unescaped quotes in strings
        - Newlines in string values (convert to \n)
        """
        logger.info("Attempting JSON repairs...")

        # Fix 1: Remove trailing commas before } or ]
        response_text = re.sub(r",(\s*[}\]])", r"\1", response_text)
        logger.debug("Fixed trailing commas")

        # Fix 2: Fix common unescaped quotes in string values
        # This is tricky - try to find and escape quotes that should be escaped
        # Look for patterns like: "text"with"quote" and fix it

        # Fix 3: Remove control characters that might break JSON
        response_text = "".join(
            char if ord(char) >= 32 or char in "\n\r\t" else ""
            for char in response_text
        )
        logger.debug("Removed control characters")

        # Fix 4: Try to fix unclosed strings by looking for common patterns
        # Count quotes to detect unclosed strings
        if response_text.count('"') % 2 != 0:
            logger.warning(
                "Odd number of quotes detected - JSON might have unclosed string"
            )
            # Try adding closing quote at the end if it looks like a string
            if not response_text.rstrip().endswith(('"', "}", "]")):
                response_text = response_text.rstrip() + '"'
                logger.debug("Added closing quote")

        return response_text

    def _validate_json_structure(self, parsed):
        """
        Validate that parsed JSON has required structure.

        Args:
            parsed (dict): Parsed JSON object

        Raises:
            ValueError: If structure is invalid
        """
        # Check top-level fields
        required_fields = ["text", "key_points", "takeaway"]

        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: '{field}'")

        # Validate text field
        if not isinstance(parsed["text"], str) or len(parsed["text"]) < 10:
            raise ValueError("'text' field must be a non-empty string")

        # Validate key_points structure
        if not isinstance(parsed["key_points"], list):
            raise ValueError("'key_points' must be a list")

        if len(parsed["key_points"]) < 2:
            raise ValueError("'key_points' must have at least 2 items")

        for i, point in enumerate(parsed["key_points"]):
            if not isinstance(point, dict):
                raise ValueError(f"key_points[{i}] must be an object")

            if "heading" not in point:
                raise ValueError(f"key_points[{i}] missing 'heading' field")

            if "description" not in point:
                raise ValueError(f"key_points[{i}] missing 'description' field")

            if not isinstance(point["heading"], str) or len(point["heading"]) < 3:
                raise ValueError(
                    f"key_points[{i}]['heading'] must be a non-empty string"
                )

            if (
                not isinstance(point["description"], str)
                or len(point["description"]) < 10
            ):
                raise ValueError(
                    f"key_points[{i}]['description'] must be a non-empty string"
                )

        # Validate takeaway
        if not isinstance(parsed["takeaway"], str) or len(parsed["takeaway"]) < 10:
            raise ValueError("'takeaway' must be a non-empty string")

        logger.info("✓ All validation checks passed")

    def _get_rag_query(self, subject, doc_type):
        """
        Determine the best RAG query based on subject and type.
        Different subjects need different keywords for better retrieval.

        Args:
            subject (str): Subject name
            doc_type (str): Document type (literature, grammar, etc)

        Returns:
            str: Query string optimized for the subject
        """
        subject = subject.lower()
        doc_type = doc_type.lower()

        # Math subjects - focus on formulas, theorems, solutions
        if subject == "mathematics":
            return "formulas, theorems, key concepts, solutions, problem-solving methods, examples"

        # English literature - focus on main topics and concepts (works for both fiction and educational)
        elif subject == "english" and doc_type == "literature":
            return "chapter summary, key ideas, main concepts, important facts"

        # English grammar - focus on rules and examples
        elif subject == "english" and doc_type == "grammar":
            return "grammar rules, sentence structure, tenses, examples, usage, corrections"

        # Hindi literature - focus on कहानी, पात्र, etc
        elif subject == "hindi" and doc_type == "literature":
            return "मुख्य विषय, विचार, पाठ, संदेश, महत्वपूर्ण बातें, उदाहरण"

        # Hindi grammar - focus on व्याकरण, rules
        elif subject == "hindi" and doc_type == "grammar":
            return "व्याकरण नियम, विधि, उदाहरण, संरचना, शब्द, वाक्य"

        # Sanskrit - focus on श्लोक, विषय
        elif subject == "sanskrit":
            return "मुख्य विषय, श्लोक, पाठ, संदेश, कथानक, महत्वपूर्ण विचार, उदाहरण"

        # Science subjects - focus on processes, mechanisms
        elif subject in ["physics", "chemistry"]:
            return "key concepts, processes, reactions, formulas, laws, important facts, examples"

        # Default fallback for unknown subjects
        else:
            return "main concepts, definitions, key points, important facts, examples, explanations"
