import re
from pathlib import Path


def normalize_text(value: str) -> str:
    value = Path(value).stem.lower()

    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"\(\d+\)", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def find_document_matches(
    query: str,
    documents,
):
    normalized_query = normalize_text(query)

    matches = []

    for document in documents:
        normalized_filename = normalize_text(document.filename)

        filename_tokens = set(normalized_filename.split())
        query_tokens = set(normalized_query.split())

        common_tokens = filename_tokens & query_tokens

        if not common_tokens:
            continue

        score = len(common_tokens) / len(filename_tokens)

        # Strong direct phrase match gets priority.
        if normalized_filename in normalized_query:
            score += 1.0

        matches.append(
            {
                "document": document,
                "score": score,
            }
        )

    matches.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches


def resolve_document_match(document_matches):
    if not document_matches:
        return None

    top_match = document_matches[0]

    # Only one matching document
    if len(document_matches) == 1:
        return top_match["document"]

    second_match = document_matches[1]

    top_score = top_match["score"]
    second_score = second_match["score"]

    # Require the best match to be meaningfully better
    if top_score >= 0.5 and (top_score - second_score) >= 0.25:
        return top_match["document"]

    return None