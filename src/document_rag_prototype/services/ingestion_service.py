from pathlib import Path

import fitz


def extract_text_from_file(file_path: Path) -> list[tuple[int | None, str]]:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return [(None, text)]

    if suffix == ".pdf":
        pages: list[tuple[int | None, str]] = []

        with fitz.open(file_path) as document:
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages.append((page_index, text))

        return pages

    raise ValueError(f"Unsupported file type: {suffix}")


def split_text_into_chunks(
    pages: list[tuple[int | None, str]],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[dict]:
    chunks: list[dict] = []
    chunk_index = 0

    for page_number, text in pages:
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": chunk_text,
                        "page_number": page_number,
                    }
                )
                chunk_index += 1

            if end >= len(text):
                break

            start = end - chunk_overlap

    return chunks