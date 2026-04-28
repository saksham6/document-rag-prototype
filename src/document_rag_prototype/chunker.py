import re

from document_rag_prototype.config import CHUNK_OVERLAP, CHUNK_SIZE
from document_rag_prototype.content_profiler import profile_content


def split_into_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def is_junk_chunk(text: str) -> bool:
    text_lower = text.lower().strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if not text_lower:
        return True

    junk_terms = [
        "table of contents",
        "contents",
        "list of figures",
        "list of tables",
        "statutory declaration",
        "table of abbreviations",
        "abbreviations",
    ]
    if any(term in text_lower for term in junk_terms):
        return True

    dot_leader_lines = sum(1 for line in lines if re.search(r"\.{2,}\s*\d+\s*$", line))
    if dot_leader_lines >= 2:
        return True

    numbered_nav_lines = 0
    for line in lines:
        if re.match(r"^\d+(\.\d+)*\s+", line) and re.search(r"\d+\s*$", line):
            numbered_nav_lines += 1

    if lines and numbered_nav_lines / len(lines) > 0.5:
        return True

    short_lines = sum(1 for line in lines if len(line.split()) <= 6)
    sentence_like = len(re.findall(r"[.!?]", text))

    if lines and short_lines / len(lines) > 0.8 and sentence_like == 0:
        return True

    return False


def chunk_paragraph_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = split_into_sentences(text)
    chunks: list[str] = []

    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence.split())

        if current_length + sentence_length <= chunk_size:
            current_chunk.append(sentence)
            current_length += sentence_length
            continue

        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            chunks.append(chunk_text)

            overlap_words = chunk_text.split()[-overlap:] if overlap > 0 else []
            overlap_text = " ".join(overlap_words)

            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
            current_length = len(" ".join(current_chunk).split())
        else:
            chunks.append(sentence)

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks


def chunk_line_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    chunks: list[str] = []

    current_chunk: list[str] = []
    current_length = 0

    for line in lines:
        line_length = len(line.split())

        if current_length + line_length <= chunk_size:
            current_chunk.append(line)
            current_length += line_length
            continue

        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            chunks.append(chunk_text)

            overlap_words = chunk_text.split()[-overlap:] if overlap > 0 else []
            overlap_text = " ".join(overlap_words)

            current_chunk = [overlap_text, line] if overlap_text else [line]
            current_length = len(" ".join(current_chunk).split())
        else:
            chunks.append(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk).strip())

    return chunks


def build_chunk_index(
    documents: list[dict],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    chunk_index: list[dict] = []

    line_chunk_size = max(40, chunk_size // 2)
    line_overlap = max(10, overlap // 2)

    for document in documents:
        text = document["text"].strip()
        if not text:
            continue

        text_mode = document.get("text_mode", "paragraph")

        if text_mode == "paragraph" or document["file_type"] == "txt":
            chunks = chunk_paragraph_text(text, chunk_size, overlap)
        elif text_mode == "line":
            chunks = chunk_line_text(text, line_chunk_size, line_overlap)
        else:
            continue

        for index, chunk in enumerate(chunks):
            chunk = chunk.strip()

            if not chunk:
                continue

            if is_junk_chunk(chunk):
                continue

            content_profile = profile_content(chunk)

            chunk_index.append(
                {
                    "source": document["source"],
                    "file_type": document["file_type"],
                    "page": document["page"],
                    "text_mode": text_mode,
                    "chunk_id": index,
                    "text": chunk,
                    **content_profile,
                }
            )

    return chunk_index