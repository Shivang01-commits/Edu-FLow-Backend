from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv


class GroqLLM:
    def __init__(self):
        load_dotenv()

    def get_llm(self):
        api_key = os.getenv("GROQ_API_KEY")
        llm = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=api_key,
    )
        return llm
