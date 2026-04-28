import re


def detect_query_type(query_lower: str) -> str:
    if any(word in query_lower for word in ["equation", "formula", "eq.", "eq ", "sigma", "beta", "parameter"]):
        return "equation"

    if any(word in query_lower for word in ["table", "tabular", "row", "column"]):
        return "table"

    if any(word in query_lower for word in ["figure", "image", "diagram", "plot", "graph"]):
        return "figure"

    if any(word in query_lower for word in ["method", "methods", "approach", "approaches", "model", "models"]):
        return "methods"

    if any(word in query_lower for word in ["result", "results", "performance", "improvement", "evaluation"]):
        return "results"

    if any(word in query_lower for word in ["conclusion", "conclude", "summary", "summarize", "overview"]):
        return "summary"

    return "general"


def detect_query_scope(query_lower: str, query_type: str) -> str:
    narrow_markers = [
        "what does",
        "define",
        "meaning of",
        "equation",
        "formula",
        "table",
        "figure",
        "diagram",
        "value of",
        "parameter",
        "sigma",
        "beta",
    ]

    broad_markers = [
        "main",
        "overall",
        "overview",
        "approaches",
        "methods",
        "components",
        "describe",
        "summarize",
        "summary",
        "discuss",
        "introduced",
    ]

    if query_type in {"equation", "table", "figure"}:
        return "narrow"

    if any(marker in query_lower for marker in narrow_markers):
        return "narrow"

    if any(marker in query_lower for marker in broad_markers):
        return "broad"

    if query_type in {"methods", "results", "summary", "general"}:
        return "broad"

    return "narrow"


def analyze_query(query: str) -> dict:
    query_lower = query.lower().strip()

    query_type = detect_query_type(query_lower)
    query_scope = detect_query_scope(query_lower, query_type)

    wants_explanation = bool(
        re.search(r"\bwhat\b|\bwhy\b|\bhow\b|\bexplain\b|\bdescribe\b", query_lower)
    )

    return {
        "query_type": query_type,
        "query_scope": query_scope,
        "wants_explanation": wants_explanation,
    }