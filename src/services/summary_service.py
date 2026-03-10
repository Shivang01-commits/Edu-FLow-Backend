from src.rag.pipeline import Pipeline
from src.llms.groq import GroqLLM

class SummaryService:
    def __init__(self):
        self.rag = Pipeline()
        self.llm = GroqLLM().get_llm()

    def summarize_chapter(self, metadata):
        # retrieve relevant chunks
        docs = self.rag.retriever(
            query="key concepts of this chapter",
            metadata=metadata
        )

        # convert chunks to context
        context = self.rag.build_context(docs)
        prompt = f"""
        You are a helpful teacher assistant.
        Use the chapter context below to summarize the chapter.

        Context:
        {context}

        Task:
        Write a clear summary of the chapter for students.

        Return output in JSON format:
        {{
            "summary": "..."
        }}
        """

        response = self.llm.invoke(prompt)

        return response.content