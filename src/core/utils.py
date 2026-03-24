from langchain_openai import ChatOpenAI
from src.config import settings
from langchain_openai import OpenAIEmbeddings


def get_llm():
    """
    Get a configured ChatOpenAI instance."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_KEY,
        temperature=0.6,
        streaming=True,
    )


def get_embeddings():
    """
    Get a configured embeddings instance.
    """
    return OpenAIEmbeddings(
        api_key=settings.OPENAI_KEY, model=settings.EMBEDDING_MODEL, dimensions=512
    )
