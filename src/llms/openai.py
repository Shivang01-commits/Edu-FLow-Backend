from openai import OpenAI
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class OpenAILLM:

    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def invoke(self, prompt: str):

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=5000
        )

        # Log token usage
        usage = response.usage
        logger.info(
            f"LLM TOKENS → prompt={usage.prompt_tokens}, "
            f"completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}"
        )



        return response.choices[0].message.content