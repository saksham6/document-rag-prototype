import re
from src.config import CHUNK_SIZE, CHUNK_OVERLAP


def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def is_junk_chunk(text):
    text_lower = text.lower().strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if not text_lower:
        return True

    # obvious front-matter/navigation keywords
    junk_terms = [
        "table of contents",
        "contents",
        "list of figures",
        "list of tables",
        "statutory declaration",
        "table of abbreviations",
        "abbreviations"
    ]
    for term in junk_terms:
        if term in text_lower:
            return True

    # dot-leader contents pattern
    dot_leader_lines = sum(1 for line in lines if re.search(r"\.{2,}\s*\d+\s*$", line))
    if dot_leader_lines >= 2:
        return True

    # too many short numbered navigation lines like:
    # 4.2 Tourism case study .... 63
    numbered_nav_lines = 0
    for line in lines:
        if re.match(r"^\d+(\.\d+)*\s+", line) and re.search(r"\d+\s*$", line):
            numbered_nav_lines += 1

    if lines and numbered_nav_lines / len(lines) > 0.5:
        return True

    # almost everything is short lines and no real sentence structure
    short_lines = sum(1 for line in lines if len(line.split()) <= 6)
    sentence_like = len(re.findall(r"[.!?]", text))

    if lines and short_lines / len(lines) > 0.8 and sentence_like == 0:
        return True

    return False


def chunk_paragraph_text(text, chunk_size, overlap):
    sentences = split_into_sentences(text)
    chunks = []

    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence.split())

        if current_length + sentence_length <= chunk_size:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
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


def chunk_line_text(text, chunk_size, overlap):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    chunks = []

    current_chunk = []
    current_length = 0

    for line in lines:
        line_length = len(line.split())

        if current_length + line_length <= chunk_size:
            current_chunk.append(line)
            current_length += line_length
        else:
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


def build_chunk_index(documents, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunk_index = []

    line_chunk_size = max(40, chunk_size // 2)
    line_overlap = max(10, overlap // 2)

    for doc in documents:
        text = doc["text"].strip()
        if not text:
            continue

        text_mode = doc.get("text_mode", "paragraph")

        if text_mode == "paragraph" or doc["file_type"] == "txt":
            chunks = chunk_paragraph_text(text, chunk_size, overlap)

        elif text_mode == "line":
            chunks = chunk_line_text(text, line_chunk_size, line_overlap)

        else:
            continue

        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()

            if not chunk:
                continue

            if is_junk_chunk(chunk):
                continue

            chunk_index.append({
                "source": doc["source"],
                "file_type": doc["file_type"],
                "page": doc["page"],
                "text_mode": text_mode,
                "chunk_id": i,
                "text": chunk
            })

    return chunk_index
