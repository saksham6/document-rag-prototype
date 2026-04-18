import os
import re
from collections import Counter
import fitz  # PyMuPDF

from src.config import MIN_CHARS_PER_PAGE


def normalize_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def clean_lines(lines):
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if re.fullmatch(r"[-–—]?\s*\d+\s*[-–—]?", line):
            continue

        alpha_count = sum(ch.isalpha() for ch in line)
        if alpha_count == 0 and len(line) < 8:
            continue

        cleaned.append(line)

    return cleaned


def remove_repeated_lines_across_pages(all_pages_lines):
    if len(all_pages_lines) < 3:
        return all_pages_lines

    counter = Counter()

    for lines in all_pages_lines:
        counter.update(set(lines))

    repeated_lines = {
        line for line, count in counter.items()
        if count >= max(3, int(0.5 * len(all_pages_lines))) and len(line.split()) <= 12
    }

    cleaned_pages = []
    for lines in all_pages_lines:
        cleaned_pages.append([line for line in lines if line not in repeated_lines])

    return cleaned_pages


def detect_text_mode(lines, page_text):
    if len(page_text.strip()) < MIN_CHARS_PER_PAGE:
        return "low_text"

    word_counts = [len(line.split()) for line in lines if line.strip()]
    if not word_counts:
        return "low_text"

    avg_words_per_line = sum(word_counts) / len(word_counts)
    short_line_ratio = sum(1 for wc in word_counts if wc <= 6) / len(word_counts)

    punctuation_count = len(re.findall(r"[.!?]", page_text))
    total_words = max(1, len(page_text.split()))
    punctuation_ratio = punctuation_count / total_words

    if avg_words_per_line >= 7 and short_line_ratio < 0.45 and punctuation_ratio >= 0.02:
        return "paragraph"

    return "line"


def is_junk_page(page_text, lines):
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

    for term in junk_terms:
        if term in text_lower:
            return True

    dot_leader_lines = sum(1 for line in lines if re.search(r"\.{2,}\s*\d+\s*$", line))
    if dot_leader_lines >= 3:
        return True

    if lines:
        short_lines = sum(1 for line in lines if len(line.split()) <= 6)
        if short_lines / len(lines) > 0.8 and dot_leader_lines >= 1:
            return True

    return False


def load_txt_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    text = normalize_text(text)

    return [{
        "source": os.path.basename(filepath),
        "file_type": "txt",
        "page": None,
        "text_mode": "paragraph",
        "text": text
    }]


def extract_page_text_with_pymupdf(page):
    blocks = page.get_text("blocks")
    blocks = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))

    lines = []
    for block in blocks:
        block_text = block[4]
        if not block_text:
            continue

        for line in block_text.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

    return lines


def load_pdf_file(filepath):
    pages_raw = []

    doc = fitz.open(filepath)

    for page_num in range(len(doc)):
        page = doc[page_num]

        try:
            lines = extract_page_text_with_pymupdf(page)
        except Exception:
            lines = []

        lines = clean_lines(lines)

        pages_raw.append({
            "page": page_num + 1,
            "lines": lines
        })

    doc.close()

    all_pages_lines = [item["lines"] for item in pages_raw]
    all_pages_lines = remove_repeated_lines_across_pages(all_pages_lines)

    documents = []

    for i, item in enumerate(pages_raw):
        lines = all_pages_lines[i]
        page_text = "\n".join(lines)
        page_text = normalize_text(page_text)

        if is_junk_page(page_text, lines):
            continue

        text_mode = detect_text_mode(lines, page_text)

        if text_mode == "low_text":
            continue

        documents.append({
            "source": os.path.basename(filepath),
            "file_type": "pdf",
            "page": item["page"],
            "text_mode": text_mode,
            "text": page_text
        })

    return documents


def load_documents(folder_path):
    documents = []

    for filename in sorted(os.listdir(folder_path)):
        filepath = os.path.join(folder_path, filename)

        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()

        try:
            if ext == ".txt":
                documents.extend(load_txt_file(filepath))
            elif ext == ".pdf":
                documents.extend(load_pdf_file(filepath))
        except Exception as e:
            print(f"Skipping {filename} because of error: {e}")

    return documents
