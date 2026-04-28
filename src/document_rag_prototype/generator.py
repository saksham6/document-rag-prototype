import re


class AnswerGenerator:
    def split_into_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def is_formula_heavy(self, text: str) -> bool:
        symbols = sum(text.count(symbol) for symbol in ["=", "(", ")", "[", "]", "{", "}"])
        words = max(1, len(text.split()))
        return (symbols / words) > 0.20

    def clean_sentences(self, sentences: list[str], query_type: str) -> list[str]:
        cleaned = []

        for sentence in sentences:
            sentence = sentence.strip()

            if len(sentence.split()) < 6:
                continue

            if re.search(r"\.{2,}\s*\d+$", sentence):
                continue

            if re.fullmatch(r"[\d\.]+\s+.*\s+\d+", sentence):
                continue

            if query_type != "equation" and self.is_formula_heavy(sentence):
                continue

            cleaned.append(sentence)

        return cleaned

    def is_duplicate(self, sentence: str, selected: list[str]) -> bool:
        words = set(re.findall(r"\b\w+\b", sentence.lower()))
        if not words:
            return True

        for existing in selected:
            existing_words = set(re.findall(r"\b\w+\b", existing.lower()))
            overlap = words.intersection(existing_words)
            ratio = len(overlap) / max(1, min(len(words), len(existing_words)))

            if ratio >= 0.70:
                return True

        return False

    def join_items(self, items: list[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"

    def extract_named_items(self, text: str) -> list[str]:
        text_lower = text.lower()
        items = []

        rules = [
            ("median template", ["median"]),
            ("gaussian template", ["gaussian"]),
            ("trapezoid template", ["trapezoid"]),
            ("centre-day alignment", ["centre day", "center day", "offset", "lead", "lag"]),
            ("weekday-dependent profile", ["weekday", "weekday-specific", "weekday specific"]),
            ("calendar-based feature", ["calendar-based feature"]),
            ("profile or kernel representation", ["profile", "kernel"]),
            ("window-based evaluation", ["window", "evaluation"]),
            ("de-seasonalisation", ["stl", "mstl", "de-season", "deseason"]),
            ("additive holiday regressor", ["binary regressor", "coefficient", "conditional mean", "additive adjustment"]),
        ]

        for label, patterns in rules:
            if any(pattern in text_lower for pattern in patterns):
                items.append(label)

        return items

    def score_broad_sentence(self, sentence: str, query_type: str) -> float:
        lower = sentence.lower()
        score = 0.0

        bad_starts = [
            "beyond the scope",
            "outside the scope",
            "however",
            "finally",
            "in contrast",
        ]
        if any(lower.startswith(start) for start in bad_starts):
            score -= 0.30

        if query_type == "methods":
            if any(word in lower for word in ["method", "approach", "model", "template", "profile", "kernel"]):
                score += 0.20
            if any(word in lower for word in ["median", "gaussian", "trapezoid", "weekday", "window", "stl", "mstl"]):
                score += 0.20

        if query_type in {"general", "summary", "methods", "results"}:
            if any(word in lower for word in ["describes", "shows", "suggests", "introduces", "contribution", "useful", "improves", "represents"]):
                score += 0.10

        return score

    def build_list_answer(self, results: list[dict], query_type: str) -> str:
        full_text = " ".join(item["text"] for item in results)
        items = self.extract_named_items(full_text)

        all_sentences = []
        for item in results:
            sentences = self.split_into_sentences(item["text"])
            sentences = self.clean_sentences(sentences, query_type)

            for sentence in sentences:
                if self.is_duplicate(sentence, all_sentences):
                    continue
                all_sentences.append(sentence)

        scored = []
        for sentence in all_sentences:
            score = self.score_broad_sentence(sentence, query_type)
            scored.append((sentence, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        explanation_sentences = []
        for sentence, _ in scored:
            if self.is_duplicate(sentence, explanation_sentences):
                continue
            explanation_sentences.append(sentence)
            if len(explanation_sentences) == 2:
                break

        if items:
            if "median template" in items and "gaussian template" in items and "trapezoid template" in items:
                header = "Main modelling components: median template, gaussian template, and trapezoid template."
            else:
                header = f"Main modelling components: {self.join_items(items)}."
        else:
            header = "Main modelling components: not clearly identifiable from the retrieved evidence."

        if explanation_sentences:
            explanation = "Explanation: " + " ".join(explanation_sentences)
            return header + "\n\n" + explanation

        return header

    def build_general_answer(self, results: list[dict], query_type: str, max_sentences: int) -> str:
        all_sentences = []

        for item in results:
            sentences = self.split_into_sentences(item["text"])
            sentences = self.clean_sentences(sentences, query_type)

            for sentence in sentences:
                if self.is_duplicate(sentence, all_sentences):
                    continue
                all_sentences.append(sentence)

        if not all_sentences:
            return "The answer is not available in the retrieved documents."

        scored = []
        for sentence in all_sentences:
            score = self.score_broad_sentence(sentence, query_type)
            scored.append((sentence, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        selected = []
        for sentence, _ in scored:
            if self.is_duplicate(sentence, selected):
                continue
            selected.append(sentence)
            if len(selected) == max_sentences:
                break

        if not selected:
            return "The answer is not available in the retrieved documents."

        return " ".join(selected)

    def generate_answer(
        self,
        query: str,
        results: list[dict],
        embedder,
        query_info: dict | None = None,
    ) -> str:
        if query_info is None:
            query_info = {"query_type": "general", "query_scope": "broad"}

        if not results:
            return "The answer is not available in the retrieved documents."

        query_lower = query.lower()
        query_type = query_info.get("query_type", "general")
        query_scope = query_info.get("query_scope", "broad")

        wants_list = any(word in query_lower for word in [
            "which", "list", "compared", "comparison", "techniques",
            "approaches", "templates", "components"
        ])

        if query_scope == "broad" and wants_list:
            return self.build_list_answer(results, query_type)

        if query_scope == "broad":
            return self.build_general_answer(results, query_type, 3)

        return self.build_general_answer(results, query_type, 2)