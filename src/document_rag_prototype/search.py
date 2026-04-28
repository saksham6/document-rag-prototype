import re

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def keyword_overlap_score(query: str, text: str) -> float:
    query_words = set(re.findall(r"\b\w+\b", query.lower()))
    text_words = set(re.findall(r"\b\w+\b", text.lower()))

    if not query_words:
        return 0.0

    overlap = query_words.intersection(text_words)
    return len(overlap) / len(query_words)


def junk_penalty(text: str) -> float:
    text_lower = text.lower()
    penalty = 0.0

    if any(term in text_lower for term in [
        "contents",
        "table of contents",
        "list of figures",
        "list of tables",
        "references",
    ]):
        penalty += 0.15

    if re.search(r"\.{2,}\s*\d+", text_lower):
        penalty += 0.15

    return penalty


def content_type_bonus(chunk: dict, query_info: dict) -> float:
    query_type = query_info.get("query_type", "general")
    content_type = chunk.get("content_type", "mixed")
    bonus = 0.0

    if chunk.get("is_noisy", False):
        bonus -= 0.30

    if query_type in {"general", "summary", "methods", "results"}:
        if content_type == "narrative":
            bonus += 0.18
        elif content_type == "equation_heavy":
            bonus -= 0.18
        elif content_type == "table_like":
            bonus -= 0.08
        elif content_type == "heading_or_caption":
            bonus -= 0.06

    elif query_type == "equation":
        if content_type == "equation_heavy":
            bonus += 0.22
        elif content_type == "narrative":
            bonus += 0.05

    elif query_type == "table":
        if content_type == "table_like":
            bonus += 0.22
        elif content_type == "narrative":
            bonus += 0.05

    elif query_type == "figure":
        if content_type == "heading_or_caption":
            bonus += 0.18
        elif content_type == "narrative":
            bonus += 0.05

    return bonus


def intent_bonus(query: str, text: str) -> float:
    query_lower = query.lower()
    text_lower = text.lower()
    bonus = 0.0

    wants_comparison = any(word in query_lower for word in [
        "which", "compare", "compared", "comparison", "differences", "alternatives"
    ])

    wants_list = any(word in query_lower for word in [
        "which", "what are", "list", "types", "techniques", "approaches", "templates", "components"
    ])

    if wants_comparison:
        if any(word in text_lower for word in ["compare", "compared", "comparison", "alternative", "alternatives"]):
            bonus += 0.18

    if wants_list:
        if any(word in text_lower for word in ["template", "templates", "techniques", "approaches", "forms", "shapes"]):
            bonus += 0.12

        named_items = ["median", "gaussian", "trapezoid"]
        hit_count = sum(1 for item in named_items if item in text_lower)

        if hit_count == 1:
            bonus += 0.12
        elif hit_count >= 2:
            bonus += 0.25

    return bonus


def exact_term_bonus(query: str, text: str) -> float:
    query_terms = set(re.findall(r"\b[a-zA-Z][a-zA-Z\-]{3,}\b", query.lower()))
    text_terms = set(re.findall(r"\b[a-zA-Z][a-zA-Z\-]{3,}\b", text.lower()))

    stop_terms = {
        "what", "does", "this", "that", "with", "from", "into", "about", "there", "their",
        "which", "section", "methods", "results", "model", "models", "technique", "techniques",
        "approach", "approaches", "template", "templates", "representation", "represent",
        "holiday", "effect", "effects", "introduced", "compared", "compare", "main", "components"
    }

    query_terms = {term for term in query_terms if term not in stop_terms}
    if not query_terms:
        return 0.0

    bonus = 0.0

    strong_terms = {
        "gaussian", "median", "trapezoid", "prophet", "sarimax", "tbats",
        "sigma", "beta", "kernel", "profile", "stl", "mstl"
    }

    for term in query_terms:
        if term in text_terms:
            if term in strong_terms:
                bonus += 0.35
            else:
                bonus += 0.12

    return bonus


def semantic_search(
    query: str,
    chunk_index: list[dict],
    chunk_embeddings,
    embedder,
    top_k: int = 3,
    source_filter: str | None = None,
    query_info: dict | None = None,
) -> list[dict]:
    if query_info is None:
        query_info = {"query_type": "general", "query_scope": "broad"}

    filtered_chunks = []
    filtered_embeddings = []

    for index, chunk in enumerate(chunk_index):
        if source_filter is None or chunk["source"] == source_filter:
            filtered_chunks.append(chunk)
            filtered_embeddings.append(chunk_embeddings[index])

    if not filtered_chunks:
        return []

    filtered_embeddings = np.array(filtered_embeddings)

    query_embedding = embedder.encode([query])
    semantic_scores = cosine_similarity(query_embedding, filtered_embeddings)[0]

    scored_results = []

    for index, chunk in enumerate(filtered_chunks):
        lexical = keyword_overlap_score(query, chunk["text"])
        penalty = junk_penalty(chunk["text"])
        content_bonus = content_type_bonus(chunk, query_info)
        extra_bonus = intent_bonus(query, chunk["text"])
        term_bonus = exact_term_bonus(query, chunk["text"])

        score = (
            (0.85 * semantic_scores[index])
            + (0.20 * lexical)
            - penalty
            + content_bonus
            + extra_bonus
            + term_bonus
        )

        scored_results.append(
            {
                "score": float(score),
                "source": chunk["source"],
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"],
                "text_mode": chunk["text_mode"],
                "content_type": chunk.get("content_type", "mixed"),
                "text": chunk["text"],
            }
        )

    scored_results.sort(key=lambda item: item["score"], reverse=True)
    return scored_results[:top_k]
