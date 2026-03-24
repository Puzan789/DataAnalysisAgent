from openai import OpenAI
from src.config import settings


class OpenAIEmbedder:
    """Class to handle text embeddings using OpenAI API."""

    def __init__(self, model_name=settings.EMBEDDING_MODEL):
        self.client = OpenAI(api_key=settings.OPENAI_KEY)
        self.model_name = model_name

    def embed_texts(self, texts):
        """Generate the emnbeddings for a list of chunks of the texts"""
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        embeddings = [item.embedding for item in response.data]
        return embeddings
