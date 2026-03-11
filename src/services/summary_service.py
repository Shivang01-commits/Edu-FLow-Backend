from src.rag.pipeline import Pipeline
from src.llms.groq import GroqLLM


class SummaryService:
    def __init__(self):
        self.rag = Pipeline()
        self.llm = GroqLLM().get_llm()

    def summarize_chapter(self, metadata):

        subject = metadata.get("subject", "").lower()
        doc_type = metadata.get("type", "").lower()

        # Selecting Query according to Subject for RAG
        if subject == "mathematics":
            query = (
                "formulas, theorems, key concepts, solutions, problem-solving methods"
            )

        elif subject == "english":
            if doc_type == "literature":
                query = (
                    "themes, characters, plot, story events, literary devices, dialogue"
                )
            else:
                query = "grammar rules, definitions ,sentence structure, examples"

        elif subject == "hindi":
            if doc_type == "literature":
                query = "कहानी, पात्र, संदेश"
            else:
                query = "व्याकरण नियम, उदाहरण, उपयोग"

        elif subject == "sanskrit":
            query = "मुख्य विषय, कथानक, पात्र, संदेश, महत्वपूर्ण श्लोक"

        else:
            query = "main concepts, definitions, key points, important facts, examples"

        # retrieve relevant chunks
        docs = self.rag.retriever(query=query, metadata=metadata, k=8)

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
