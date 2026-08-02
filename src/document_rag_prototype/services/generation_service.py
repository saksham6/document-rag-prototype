import os

from document_rag_prototype.services.embedding_service import get_openai_client
from document_rag_prototype.api.schemas.models import SearchResult


def build_context(chunks: list[SearchResult]) -> str:
    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        page_text = f", page {chunk.page_number}" if chunk.page_number is not None else ""

        context_parts.append(
            f"[Source {index}: {chunk.filename}{page_text}, chunk_id={chunk.chunk_id}]\n"
            f"{chunk.content}"
        )

    return "\n\n".join(context_parts)


async def generate_answer(
    question: str,
    chunks: list[SearchResult],
) -> str:
    if not chunks:
        return "I could not find relevant information in the uploaded documents."

    context = build_context(chunks)

    client = get_openai_client()

    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document question-answering assistant. "
                    "Answer only using the provided context. "
                    "If the context does not contain the answer, say that the information was not found in the documents."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Context:\n{context}\n\n"
                    "Give a clear answer based only on the context."
                ),
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content or ""



    