from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv


class QwenLLM:
    def __init__(self):
        load_dotenv()

    def get_llm(self):

        llm = ChatOpenAI(
            model="Qwen/Qwen3.5-397B-A17B",
            openai_api_key=os.getenv("HF_TOKEN"),
            openai_api_base="https://router.huggingface.co/v1",
            temperature=0.3,
            max_tokens=2048,
        )

        return llm
