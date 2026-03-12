import logging
import json
import re


logger = logging.getLogger(__name__)


class LLMJsonParser:
    def __init__(self, llm, max_retries=2, retry_delay=1):
        self.llm = llm
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def invoke_llm_with_retry(self, prompt, max_retries=2):
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

        self._validate_json_structure(parsed)
        logger.info("✓ JSON validation successful")
        return parsed

    def _clean_response(self, response_text):
        """
        Remove markdown code blocks and extra whitespace.
        """
        response_text = response_text.strip()

        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]

        if response_text.endswith("```"):
            response_text = response_text[:-3]

        return response_text.strip()

    def _repair_json(self, response_text):
        """
        Attempt to fix common JSON issues.
        """
        logger.info("Attempting JSON repairs...")

        response_text = re.sub(r",(\s*[}\]])", r"\1", response_text)

        response_text = "".join(
            char if ord(char) >= 32 or char in "\n\r\t" else ""
            for char in response_text
        )

        if response_text.count('"') % 2 != 0:
            if not response_text.rstrip().endswith(('"', "}", "]")):
                response_text = response_text.rstrip() + '"'

        return response_text

    def _validate_json_structure(self, parsed):
        """
        Validate that parsed JSON has required structure.
        """
        required_fields = ["text", "key_points", "takeaway"]

        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: '{field}'")

        if not isinstance(parsed["text"], str) or len(parsed["text"]) < 10:
            raise ValueError("'text' field must be a non-empty string")

        if not isinstance(parsed["key_points"], list):
            raise ValueError("'key_points' must be a list")

        if len(parsed["key_points"]) < 2:
            raise ValueError("'key_points' must have at least 2 items")

        for i, point in enumerate(parsed["key_points"]):
            if not isinstance(point, dict):
                raise ValueError(f"key_points[{i}] must be an object")

            if "heading" not in point or "description" not in point:
                raise ValueError(f"key_points[{i}] missing required fields")

        if not isinstance(parsed["takeaway"], str) or len(parsed["takeaway"]) < 10:
            raise ValueError("'takeaway' must be a non-empty string")

        logger.info("✓ All validation checks passed")
