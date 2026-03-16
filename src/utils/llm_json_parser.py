import logging
import json
import re
import time

logger = logging.getLogger(__name__)


class LLMJsonParser:
    def __init__(self, llm, max_retries=2, retry_delay=1):
        self.llm = llm
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def invoke_llm_with_retry(self, prompt, validation_type="summary", max_retries=2):
        """
        Invoke LLM with retry logic.
        If first attempt fails to produce valid JSON, retry.

        Args:
            prompt (str): The prompt to send to LLM
            validation_type (str): Type of validation to perform ("summary", "quiz", "qa", etc.)
            max_retries (int): Number of retries if JSON parsing fails

        Returns:
            dict: Parsed and validated JSON response

        Raises:
            ValueError: If all retries fail
        """
        attempt = 0

        while attempt <= max_retries:
            try:
                logger.info(f"LLM attempt {attempt + 1}/{max_retries + 1} (validation_type: {validation_type})")

                # Invoke LLM
                response_text = self.llm.invoke(prompt)

                logger.info(f"LLM response preview: {response_text[:500]}...")
    
                if not response_text or not response_text.strip():
                    raise ValueError("LLM returned empty content")
                
                # Log response length for debugging
                logger.info(f"LLM response length: {len(response_text)}")

                # Try to parse and validate
                parsed_data = self._parse_and_validate_json(response_text, validation_type)

                logger.info(f"✓ Successfully parsed and validated JSON on attempt {attempt + 1}")
                return parsed_data

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"✗ Error on attempt {attempt + 1}: {e}")

                # If this was the last attempt, raise
                if attempt >= max_retries:
                    logger.error(f"Failed after {max_retries + 1} attempts")
                    raise ValueError(
                        f"Failed to generate valid JSON after {max_retries + 1} attempts: {e}"
                    )

                # Otherwise, retry
                attempt += 1
                logger.info(f"Retrying... (attempt {attempt + 1})")
                time.sleep(self.retry_delay)

        raise ValueError(f"Failed to generate {validation_type} after {max_retries + 1} attempts")

    def _parse_and_validate_json(self, response_text, validation_type="summary"):
        """
        Parse and validate JSON response from LLM based on validation type.
        
        Args:
            response_text (str): Raw response from LLM
            validation_type (str): Type of validation ("summary", "quiz", "qa", etc.)
        
        Returns:
            dict: Validated parsed JSON
        """
        response_text = self._clean_response(response_text)

        try:
            parsed = json.loads(response_text)
            logger.info("✓ Direct JSON parsing successful")
        except json.JSONDecodeError as e:
            logger.warning(f"Direct parsing failed: {e}")
            logger.info("Attempting to repair JSON...")

            try:
                response_text = self._repair_json(response_text)
                parsed = json.loads(response_text)
                logger.info("✓ Repaired JSON parsing successful")
            except json.JSONDecodeError as repair_error:
                logger.error(f"JSON repair failed: {repair_error}")
                raise repair_error

        # Call appropriate validation method based on type
        self._validate_json_structure(parsed, validation_type)
        logger.info(f"✓ JSON validation successful for type: {validation_type}")
        return parsed

    def _clean_response(self, response_text):
        """
        Remove markdown code blocks and extra whitespace.
        Extract JSON from response.
        """
        response_text = response_text.strip()
        
        # Remove markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]

        if response_text.endswith("```"):
            response_text = response_text[:-3]

        # Extract JSON object using regex
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            response_text = match.group()
    
        return response_text.strip()

    def _repair_json(self, response_text):
        """
        Attempt to fix common JSON issues.
        """
        logger.info("Attempting JSON repairs...")

        # Fix trailing commas before closing brackets
        response_text = re.sub(r",(\s*[}\]])", r"\1", response_text)

        # Remove non-printable characters (except newlines, tabs)
        response_text = "".join(
            char if ord(char) >= 32 or char in "\n\r\t" else ""
            for char in response_text
        )

        # Fix missing commas between consecutive fields
        response_text = re.sub(r'"}\s*"{', '"}, {"', response_text)
        
        return response_text

    def _validate_json_structure(self, parsed, validation_type="summary"):
        """
        Route to appropriate validation method based on type.
        
        Args:
            parsed (dict): Parsed JSON object
            validation_type (str): Type of validation to perform
        
        Raises:
            ValueError: If validation fails
        """
        if validation_type == "summary":
            self._validate_summary_json(parsed)
        elif validation_type == "quiz":
            self._validate_quiz_json(parsed)
        elif validation_type == "ppt":
            self._validate_ppt_json(parsed)
        elif validation_type == "exercise_extraction":
            self._validate_exercise_extraction_json(parsed)  
        elif validation_type == "exercise_answering":
            self._validate_exercise_answering_json(parsed)
        else:
            raise ValueError(f"Unknown validation type: {validation_type}")

    def _validate_summary_json(self, parsed):
        """
        Validate summary JSON structure.
        Expected structure:
        {
          "summary": {
            "heading_1": "text",
            "heading_2": "text",
            ...
          },
          "key_points": ["point1", "point2", ...]
        }
        """
        logger.info("Validating summary JSON structure...")

        # Check top-level fields
        if "summary" not in parsed:
            raise ValueError("Missing required field: 'summary'")
        
        if "key_points" not in parsed:
            raise ValueError("Missing required field: 'key_points'")

        # Validate summary object
        if not isinstance(parsed["summary"], dict):
            raise ValueError("'summary' must be an object/dict")
        
        if len(parsed["summary"]) < 1:
            raise ValueError("'summary' must have at least one heading")

        for heading_key, heading_text in parsed["summary"].items():
            if not isinstance(heading_text, str) or len(heading_text.strip()) < 10:
                raise ValueError(f"'{heading_key}' must be a non-empty string with meaningful content")

        # Validate key_points array
        if not isinstance(parsed["key_points"], list):
            raise ValueError("'key_points' must be an array/list")

        if len(parsed["key_points"]) < 3:
            raise ValueError("'key_points' must have at least 3 items")

        for i, point in enumerate(parsed["key_points"]):
            if not isinstance(point, str) or len(point.strip()) < 5:
                raise ValueError(f"key_points[{i}] must be a non-empty string")

        logger.info("✓ All summary validation checks passed")

    def _validate_quiz_json(self, parsed):
        """
        Validate quiz JSON structure.
        Expected structure:
        {
          "questions": [
            {
              "id": 1,
              "question_text": "...",
              "options": {
                "A": "...",
                "B": "...",
                "C": "...",
                "D": "..."
              },
              "correct_answer": "A",
              "explanation": "..."
            }
          ]
        }
        """
        logger.info("Validating quiz JSON structure...")

        # Check top-level field
        if "questions" not in parsed:
            raise ValueError("Missing required field: 'questions'")

        # Validate questions array
        if not isinstance(parsed["questions"], list):
            raise ValueError("'questions' must be an array/list")

        if len(parsed["questions"]) != 10:
            raise ValueError("'questions' must contain exactly 10 questions")

        # Validate each question
        for i, question in enumerate(parsed["questions"]):
            if not isinstance(question, dict):
                raise ValueError(f"questions[{i}] must be an object/dict")

            # Check required fields
            required_fields = ["id", "question_text", "options", "correct_answer", "explanation"]
            for field in required_fields:
                if field not in question:
                    raise ValueError(f"questions[{i}] missing required field: '{field}'")

            # Validate id
            if not isinstance(question["id"], int) or question["id"] != (i + 1):
                raise ValueError(f"questions[{i}] 'id' must be an integer matching position (expected {i + 1})")

            # Validate question_text
            if not isinstance(question["question_text"], str) or len(question["question_text"].strip()) < 5:
                raise ValueError(f"questions[{i}] 'question_text' must be a non-empty string")

            # Validate options
            if not isinstance(question["options"], dict):
                raise ValueError(f"questions[{i}] 'options' must be an object/dict")

            option_keys = set(question["options"].keys())
            expected_keys = {"A", "B", "C", "D"}
            if option_keys != expected_keys:
                raise ValueError(f"questions[{i}] 'options' must have exactly keys: A, B, C, D")

            for option_key, option_text in question["options"].items():
                if not isinstance(option_text, str) or len(option_text.strip()) < 2:
                    raise ValueError(f"questions[{i}] option '{option_key}' must be a non-empty string")

            # Validate correct_answer
            if question["correct_answer"] not in ["A", "B", "C", "D"]:
                raise ValueError(f"questions[{i}] 'correct_answer' must be one of: A, B, C, D")

            # Validate explanation
            if not isinstance(question["explanation"], str) or len(question["explanation"].strip()) < 5:
                raise ValueError(f"questions[{i}] 'explanation' must be a non-empty string")

        logger.info("✓ All quiz validation checks passed")

    def _validate_ppt_json(self, parsed):
        """
        Validate PPT JSON structure.
        Expected structure:
        {
        "slides": [
            {
            "slide_number": 1,
            "slide_type": "title",
            "title": "...",
            "subtitle": "..."
            },
            {
            "slide_number": 2,
            "slide_type": "content",
            "title": "...",
            "bullet_points": ["point1", "point2", ...]
            },
            {
            "slide_number": 3,
            "slide_type": "summary",
            "title": "...",
            "bullet_points": ["point1", "point2", ...]
            }
        ]
        }
        """
        logger.info("Validating PPT JSON structure...")

        # Check top-level field
        if "slides" not in parsed:
            raise ValueError("Missing required field: 'slides'")

        # Validate slides array
        if not isinstance(parsed["slides"], list):
            raise ValueError("'slides' must be an array/list")

        if len(parsed["slides"]) < 4 or len(parsed["slides"]) > 10:
            raise ValueError("'slides' must contain between 4 and 10 slides")

        # Validate each slide
        for i, slide in enumerate(parsed["slides"]):
            if not isinstance(slide, dict):
                raise ValueError(f"slides[{i}] must be an object/dict")

            # Check required fields based on slide type
            # Title slides have: slide_number, slide_type, title, subtitle
            # Other slides have: slide_number, slide_type, title, bullet_points
            if slide.get("slide_type") == "title":
                required_fields = ["slide_number", "slide_type", "title", "subtitle"]
            else:  # content, summary, conclusion
                required_fields = ["slide_number", "slide_type", "title", "bullet_points"]
            
            for field in required_fields:
                if field not in slide:
                    raise ValueError(f"slides[{i}] missing required field: '{field}'")

            # Validate slide_number
            if not isinstance(slide["slide_number"], int) or slide["slide_number"] != (i + 1):
                raise ValueError(f"slides[{i}] 'slide_number' must be an integer matching position (expected {i + 1})")

            # Validate slide_type
            valid_types = ["title", "content", "summary", "conclusion"]
            if slide["slide_type"] not in valid_types:
                raise ValueError(f"slides[{i}] 'slide_type' must be one of: {', '.join(valid_types)}")

            # Validate title
            if not isinstance(slide["title"], str) or len(slide["title"].strip()) < 2:
                raise ValueError(f"slides[{i}] 'title' must be a non-empty string")

            # Validate title slide specific requirements
            if slide["slide_type"] == "title":
                if not isinstance(slide["subtitle"], str) or len(slide["subtitle"].strip()) < 2:
                    raise ValueError(f"slides[{i}] 'subtitle' must be a non-empty string")
            else:
                # Validate bullet_points for non-title slides
                if not isinstance(slide["bullet_points"], list):
                    raise ValueError(f"slides[{i}] 'bullet_points' must be an array/list")

                if len(slide["bullet_points"]) < 1:
                    raise ValueError(f"slides[{i}] 'bullet_points' must have at least 1 item")

                for j, point in enumerate(slide["bullet_points"]):
                    if not isinstance(point, str) or len(point.strip()) < 2:
                        raise ValueError(f"slides[{i}] bullet_points[{j}] must be a non-empty string")

            # Validate slide order (must start with title)
            if parsed["slides"][0]["slide_type"] != "title":
                raise ValueError("First slide must be of type 'title'")

            # Validate last slide is summary or conclusion
            last_slide_type = parsed["slides"][-1]["slide_type"]
            if last_slide_type not in ["summary", "conclusion"]:
                raise ValueError("Last slide must be of type 'summary' or 'conclusion'")

        logger.info("✓ All PPT validation checks passed")

    def _validate_exercise_extraction_json(self, parsed):
        """
        Validate exercise extraction JSON structure.
        Expected structure:
        {
        "exercises": [
            {
            "section_title": "...",
            "questions": [
                {
                "question_number": "1",
                "question_text": "...",
                "type": "fill_blank|short_answer|long_answer|true_false|mcq|match|multiple_select|numerical|other",
                "based_on_image": false,
                "answer": null
                }
            ]
            }
        ]
        }
        """
        logger.info("Validating exercise extraction JSON structure...")

        # Check top-level field
        if "exercises" not in parsed:
            raise ValueError("Missing required field: 'exercises'")

        # Validate exercises array
        if not isinstance(parsed["exercises"], list):
            raise ValueError("'exercises' must be an array/list")

        if len(parsed["exercises"]) < 1:
            raise ValueError("'exercises' must contain at least 1 section")

        # Valid question types
        valid_types = ["fill_blank", "short_answer", "long_answer", "true_false", "mcq", "match", "multiple_select", "numerical", "other"]

        # Validate each section
        for i, section in enumerate(parsed["exercises"]):
            if not isinstance(section, dict):
                raise ValueError(f"exercises[{i}] must be an object/dict")

            # Check required fields
            if "section_title" not in section:
                raise ValueError(f"exercises[{i}] missing required field: 'section_title'")

            if "questions" not in section:
                raise ValueError(f"exercises[{i}] missing required field: 'questions'")

            # Validate section_title
            if not isinstance(section["section_title"], str) or len(section["section_title"].strip()) < 1:
                raise ValueError(f"exercises[{i}] 'section_title' must be a non-empty string")

            # Validate questions array
            if not isinstance(section["questions"], list):
                raise ValueError(f"exercises[{i}] 'questions' must be an array/list")

            if len(section["questions"]) < 1:
                raise ValueError(f"exercises[{i}] 'questions' must have at least 1 question")

            # Validate each question
            for j, question in enumerate(section["questions"]):
                if not isinstance(question, dict):
                    raise ValueError(f"exercises[{i}] questions[{j}] must be an object/dict")

                # Check required fields
                required_fields = ["question_number", "question_text", "type", "based_on_image", "answer"]
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"exercises[{i}] questions[{j}] missing required field: '{field}'")

                # Validate question_number
                if not isinstance(question["question_number"], str) or len(question["question_number"].strip()) < 1:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'question_number' must be a non-empty string")

                # Validate question_text
                if not isinstance(question["question_text"], str) or len(question["question_text"].strip()) < 5:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'question_text' must be a meaningful string (at least 5 characters)")

                # Validate type
                if question["type"] not in valid_types:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'type' must be one of: {', '.join(valid_types)}")

                # Validate based_on_image
                if not isinstance(question["based_on_image"], bool):
                    raise ValueError(f"exercises[{i}] questions[{j}] 'based_on_image' must be a boolean (true/false)")

                # Validate answer field exists (can be null initially)
                if "answer" not in question:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'answer' field is required (can be null)")

        logger.info("✓ All exercise extraction validation checks passed")


    def _validate_exercise_answering_json(self, parsed):
        """
        Validate exercise answering JSON structure.
        Expected structure (same as extraction but with answers populated):
        {
        "exercises": [
            {
            "section_title": "...",
            "questions": [
                {
                "question_number": "1",
                "question_text": "...",
                "type": "fill_blank|short_answer|long_answer|true_false|mcq|match|multiple_select|numerical|other",
                "based_on_image": false,
                "answer": "answer text or 'Not found in chapter' or 'Cannot answer - question requires image reference'"
                }
            ]
            }
        ]
        }
        """
        logger.info("Validating exercise answering JSON structure...")

        # Check top-level field
        if "exercises" not in parsed:
            raise ValueError("Missing required field: 'exercises'")

        # Validate exercises array
        if not isinstance(parsed["exercises"], list):
            raise ValueError("'exercises' must be an array/list")

        if len(parsed["exercises"]) < 1:
            raise ValueError("'exercises' must contain at least 1 section")

        # Valid question types
        valid_types = ["fill_blank", "short_answer", "long_answer", "true_false", "mcq", "match", "multiple_select", "numerical", "other"]

        # Validate each section
        for i, section in enumerate(parsed["exercises"]):
            if not isinstance(section, dict):
                raise ValueError(f"exercises[{i}] must be an object/dict")

            # Check required fields
            if "section_title" not in section:
                raise ValueError(f"exercises[{i}] missing required field: 'section_title'")

            if "questions" not in section:
                raise ValueError(f"exercises[{i}] missing required field: 'questions'")

            # Validate section_title
            if not isinstance(section["section_title"], str) or len(section["section_title"].strip()) < 1:
                raise ValueError(f"exercises[{i}] 'section_title' must be a non-empty string")

            # Validate questions array
            if not isinstance(section["questions"], list):
                raise ValueError(f"exercises[{i}] 'questions' must be an array/list")

            if len(section["questions"]) < 1:
                raise ValueError(f"exercises[{i}] 'questions' must have at least 1 question")

            # Validate each question
            for j, question in enumerate(section["questions"]):
                if not isinstance(question, dict):
                    raise ValueError(f"exercises[{i}] questions[{j}] must be an object/dict")

                # Check required fields
                required_fields = ["question_number", "question_text", "type", "based_on_image", "answer"]
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"exercises[{i}] questions[{j}] missing required field: '{field}'")

                # Validate question_number
                if not isinstance(question["question_number"], str) or len(question["question_number"].strip()) < 1:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'question_number' must be a non-empty string")

                # Validate question_text
                if not isinstance(question["question_text"], str) or len(question["question_text"].strip()) < 5:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'question_text' must be a meaningful string (at least 5 characters)")

                # Validate type
                if question["type"] not in valid_types:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'type' must be one of: {', '.join(valid_types)}")

                # Validate based_on_image
                if not isinstance(question["based_on_image"], bool):
                    raise ValueError(f"exercises[{i}] questions[{j}] 'based_on_image' must be a boolean (true/false)")

                # Validate answer field
                if not isinstance(question["answer"], str) or len(question["answer"].strip()) < 1:
                    raise ValueError(f"exercises[{i}] questions[{j}] 'answer' must be a non-empty string")

                # Special validation for image-based questions
                if question["based_on_image"] and question["answer"] != "Cannot answer - question requires image reference":
                    logger.warning(f"exercises[{i}] questions[{j}] is marked as image-based but answer is not the standard message")

        logger.info("✓ All exercise answering validation checks passed")