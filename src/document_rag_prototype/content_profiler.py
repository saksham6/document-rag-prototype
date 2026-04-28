import re


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def symbol_ratio(text: str) -> float:
    symbols = sum(text.count(symbol) for symbol in ["=", "(", ")", "[", "]", "{", "}", "+", "-", "*", "/", "^"])
    words = max(1, word_count(text))
    return symbols / words


def line_list(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def is_table_like(text: str) -> bool:
    lines = line_list(text)

    if len(lines) < 2:
        return False

    many_numeric_lines = 0
    repeated_spacing_lines = 0

    for line in lines:
        numbers = len(re.findall(r"\d", line))
        words = max(1, len(line.split()))

        if numbers >= 3 and words <= 12:
            many_numeric_lines += 1

        if re.search(r"\s{2,}", line):
            repeated_spacing_lines += 1

    if many_numeric_lines / len(lines) > 0.4:
        return True

    if repeated_spacing_lines / len(lines) > 0.4:
        return True

    if "table" in text.lower():
        return True

    return False


def is_heading_or_caption(text: str) -> bool:
    lines = line_list(text)

    if len(lines) > 3:
        return False

    text_lower = text.lower().strip()

    if text_lower.startswith("figure") or text_lower.startswith("fig."):
        return True

    if text_lower.startswith("table"):
        return True

    if word_count(text) <= 12 and not text.endswith("."):
        return True

    return False


def is_list_like(text: str) -> bool:
    lines = line_list(text)

    if len(lines) < 2:
        return False

    bullet_lines = 0
    for line in lines:
        if re.match(r"^[-•*]\s+", line):
            bullet_lines += 1
        elif re.match(r"^\d+[\.\)]\s+", line):
            bullet_lines += 1

    return bullet_lines / len(lines) > 0.4


def is_equation_heavy(text: str) -> bool:
    text_lower = text.lower()

    if "equation" in text_lower or "eq." in text_lower:
        return True

    if symbol_ratio(text) > 0.18:
        return True

    if re.search(r"[a-zA-Z]\s*=\s*[\w\d]", text):
        return True

    return False


def is_noisy(text: str) -> bool:
    text_lower = text.lower()

    if re.search(r"\.{2,}\s*\d+", text):
        return True

    junk_terms = [
        "table of contents",
        "contents",
        "list of figures",
        "list of tables",
        "references",
    ]

    if any(term in text_lower for term in junk_terms):
        return True

    words = max(1, word_count(text))
    alpha_chars = sum(char.isalpha() for char in text)
    digit_chars = sum(char.isdigit() for char in text)

    if alpha_chars < 20 and digit_chars > 10:
        return True

    if words < 6:
        return True

    return False


def is_narrative(text: str) -> bool:
    if is_noisy(text):
        return False

    if is_equation_heavy(text):
        return False

    if is_table_like(text):
        return False

    sentences = re.findall(r"[.!?]", text)
    words = word_count(text)

    if words >= 20 and len(sentences) >= 1:
        return True

    return False


def profile_content(text: str) -> dict:
    content_type = "mixed"

    if is_noisy(text):
        content_type = "noisy"
    elif is_heading_or_caption(text):
        content_type = "heading_or_caption"
    elif is_table_like(text):
        content_type = "table_like"
    elif is_list_like(text):
        content_type = "list_like"
    elif is_equation_heavy(text):
        content_type = "equation_heavy"
    elif is_narrative(text):
        content_type = "narrative"

    return {
        "content_type": content_type,
        "is_narrative": content_type == "narrative",
        "is_equation_heavy": content_type == "equation_heavy",
        "is_table_like": content_type == "table_like",
        "is_heading_or_caption": content_type == "heading_or_caption",
        "is_list_like": content_type == "list_like",
        "is_noisy": content_type == "noisy",
    }