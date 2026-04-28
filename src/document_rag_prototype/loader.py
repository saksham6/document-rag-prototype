from pathlib import Path
import re
from collections import Counter

import fitz

from document_rag_prototype.config import MIN_CHARS_PER_PAGE


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def clean_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if re.fullmatch(r"[-–—]?\s*\d+\s*[-–—]?", line):
            continue

        alpha_count = sum(char.isalpha() for char in line)
        if alpha_count == 0 and len(line) < 8:
            continue

        cleaned.append(line)

    return cleaned


def remove_repeated_lines_across_pages(all_pages_lines: list[list[str]]) -> list[list[str]]:
    if len(all_pages_lines) < 3:
        return all_pages_lines

    counter: Counter[str] = Counter()

    for lines in all_pages_lines:
        counter.update(set(lines))

    repeated_lines = {
        line
        for line, count in counter.items()
        if count >= max(3, int(0.5 * len(all_pages_lines))) and len(line.split()) <= 12
    }

    return [
        [line for line in lines if line not in repeated_lines]
        for lines in all_pages_lines
    ]


def detect_text_mode(lines: list[str], page_text: str) -> str:
    if len(page_text.strip()) < MIN_CHARS_PER_PAGE:
        return "low_text"

    word_counts = [len(line.split()) for line in lines if line.strip()]
    if not word_counts:
        return "low_text"

    avg_words_per_line = sum(word_counts) / len(word_counts)
    short_line_ratio = sum(1 for count in word_counts if count <= 6) / len(word_counts)

    punctuation_count = len(re.findall(r"[.!?]", page_text))
    total_words = max(1, len(page_text.split()))
    punctuation_ratio = punctuation_count / total_words

    if avg_words_per_line >= 7 and short_line_ratio < 0.45 and punctuation_ratio >= 0.02:
        return "paragraph"

    return "line"


def is_junk_page(page_text: str, lines: list[str]) -> bool:
    text_lower = page_text.lower()

    junk_terms = [
        "table of contents",
        "contents",
        "list of figures",
        "list of tables",
        "statutory declaration",
        "declaration",
        "table of abbreviations",
        "abbreviations",
    ]

    if any(term in text_lower for term in junk_terms):
        return True

    dot_leader_lines = sum(1 for line in lines if re.search(r"\.{2,}\s*\d+\s*$", line))
    if dot_leader_lines >= 3:
        return True

    if lines:
        short_lines = sum(1 for line in lines if len(line.split()) <= 6)
        if short_lines / len(lines) > 0.8 and dot_leader_lines >= 1:
            return True

    return False


def extract_page_lines(page: fitz.Page) -> list[str]:
    blocks = page.get_text("blocks")
    blocks = sorted(blocks, key=lambda block: (round(block[1], 1), round(block[0], 1)))

    lines: list[str] = []

    for block in blocks:
        block_text = block[4]
        if not block_text:
            continue

        for line in block_text.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

    return lines


def load_txt_file(filepath: Path) -> list[dict]:
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    text = normalize_text(text)

    return [
        {
            "source": filepath.name,
            "file_type": "txt",
            "page": None,
            "text_mode": "paragraph",
            "text": text,
        }
    ]


def load_pdf_file(filepath: Path) -> list[dict]:
    pages_raw: list[dict] = []

    with fitz.open(filepath) as document:
        for page_index in range(len(document)):
            page = document[page_index]

            try:
                lines = extract_page_lines(page)
            except Exception:
                lines = []

            pages_raw.append(
                {
                    "page": page_index + 1,
                    "lines": clean_lines(lines),
                }
            )

    all_pages_lines = [page["lines"] for page in pages_raw]
    cleaned_pages = remove_repeated_lines_across_pages(all_pages_lines)

    documents: list[dict] = []

    for page_info, lines in zip(pages_raw, cleaned_pages):
        page_text = normalize_text("\n".join(lines))

        if is_junk_page(page_text, lines):
            continue

        text_mode = detect_text_mode(lines, page_text)
        if text_mode == "low_text":
            continue

        documents.append(
            {
                "source": filepath.name,
                "file_type": "pdf",
                "page": page_info["page"],
                "text_mode": text_mode,
                "text": page_text,
            }
        )

    return documents


def load_documents(folder_path: str | Path) -> list[dict]:
    folder = Path(folder_path)
    documents: list[dict] = []

    for filepath in sorted(folder.iterdir()):
        if not filepath.is_file():
            continue

        try:
            if filepath.suffix.lower() == ".txt":
                documents.extend(load_txt_file(filepath))
            elif filepath.suffix.lower() == ".pdf":
                documents.extend(load_pdf_file(filepath))
        except Exception as error:
            print(f"Skipping {filepath.name} because of error: {error}")

    return documents