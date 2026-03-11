import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface.embeddings import HuggingFaceEndpointEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    Filter,
    FieldCondition,
    MatchValue,
)

load_dotenv()

hf_api_key = os.getenv("HF_TOKEN")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
qdrant_url = os.getenv("QUADRANT_ENDPOINT")

COLLECTION_NAME = "chapters"


class Pipeline:
    def load_pdf(self, file_path: str):
        """Load pdf and return langchain documents"""
        loader = PyMuPDFLoader(file_path)
        docs = loader.load()
        return docs

    def split_documents(self, documents):
        """Split documents into smaller chunks"""
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        chunks = splitter.split_documents(documents)
        return chunks

    def embed_documents(self):
        embeddings = HuggingFaceEndpointEmbeddings(
            huggingfacehub_api_token=hf_api_key,
            model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        return embeddings

    def get_vectors(self, embeddings):

        client = QdrantClient(api_key=qdrant_api_key, url=qdrant_url)

        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME not in collection_names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

            # create indexes for filtering
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.class",
                field_schema=PayloadSchemaType.INTEGER,
            )

            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.subject",
                field_schema=PayloadSchemaType.KEYWORD,
            )

            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.chapter",
                field_schema=PayloadSchemaType.INTEGER,
            )

            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.type",
                field_schema=PayloadSchemaType.KEYWORD
            )

            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.medium",
                field_schema=PayloadSchemaType.KEYWORD
            )

        vectorstore = QdrantVectorStore(
            client=client, collection_name=COLLECTION_NAME, embedding=embeddings
        )

        return vectorstore

    def pipeline(self, file_path: str, metadata: dict = None):
        documents = self.load_pdf(file_path)
        chunks = self.split_documents(documents)
        if metadata:
            for chunk in chunks:
                chunk.metadata.update(metadata)
        embeddings = self.embed_documents()
        vector_store = self.get_vectors(embeddings)
        vector_store.add_documents(chunks)
        return {"status": "success", "chunks_added": len(chunks)}

    def retriever(self, query, metadata=None, k=8):

        embeddings = self.embed_documents()
        vector_store = self.get_vectors(embeddings)
        search_filter = None
        if metadata:
            search_filter = Filter(
                must=[
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                    for key, value in metadata.items()
                ]
            )
        docs = vector_store.similarity_search(query=query, k=k, filter=search_filter)

        return docs

    def build_context(self, docs):
        context = "\n\n".join([doc.page_content for doc in docs])
        return context
