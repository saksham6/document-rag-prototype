import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def keyword_overlap_score(query, text):
    query_words = set(re.findall(r"\b\w+\b", query.lower()))
    text_words = set(re.findall(r"\b\w+\b", text.lower()))

    if not query_words:
        return 0.0

    overlap = query_words.intersection(text_words)
    return len(overlap) / len(query_words)


def junk_penalty(text):
    text_lower = text.lower()
    penalty = 0.0

    junk_terms = [
        "contents",
        "table of contents",
        "list of figures",
        "list of tables",
        "references"
    ]

    for term in junk_terms:
        if term in text_lower:
            penalty += 0.15

    if re.search(r"\.{2,}\s*\d+", text_lower):
        penalty += 0.15

    return penalty


def semantic_search(query, chunk_index, chunk_embeddings, embedder, top_k=3, source_filter=None):
    filtered_chunks = []
    filtered_embeddings = []

    for i, chunk in enumerate(chunk_index):
        if source_filter is None or chunk["source"] == source_filter:
            filtered_chunks.append(chunk)
            filtered_embeddings.append(chunk_embeddings[i])

    if not filtered_chunks:
        return []

    filtered_embeddings = np.array(filtered_embeddings)

    query_embedding = embedder.encode([query])
    semantic_scores = cosine_similarity(query_embedding, filtered_embeddings)[0]

    final_scores = []

    for i, chunk in enumerate(filtered_chunks):
        lexical_score = keyword_overlap_score(query, chunk["text"])
        penalty = junk_penalty(chunk["text"])

        score = (0.85 * semantic_scores[i]) + (0.20 * lexical_score) - penalty
        final_scores.append(score)

    final_scores = np.array(final_scores)
    top_indices = np.argsort(final_scores)[::-1][:top_k]

    results = []

    for idx in top_indices:
        results.append({
            "score": float(final_scores[idx]),
            "source": filtered_chunks[idx]["source"],
            "page": filtered_chunks[idx]["page"],
            "chunk_id": filtered_chunks[idx]["chunk_id"],
            "text_mode": filtered_chunks[idx]["text_mode"],
            "text": filtered_chunks[idx]["text"]
        })

    return results
