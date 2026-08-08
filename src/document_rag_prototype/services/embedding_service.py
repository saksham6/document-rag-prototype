import os

from openai import OpenAI

from document_rag_prototype.core.config import (
    OPENAI_EMBEDDING_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
)


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    return OpenAI(api_key=api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_openai_client()

    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=texts,
        dimensions=OPENAI_EMBEDDING_DIMENSIONS,
    )

    return [item.embedding for item in response.data]