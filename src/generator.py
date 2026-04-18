import re
from sklearn.metrics.pairwise import cosine_similarity


class AnswerGenerator:
    def split_into_sentences(self, text):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def clean_sentences(self, sentences):
        cleaned = []

        for s in sentences:
            if len(s.split()) < 6:
                continue

            if re.search(r"\.{2,}\s*\d+$", s):
                continue

            if re.fullmatch(r"[\d\.]+\s+.*\s+\d+", s):
                continue

            cleaned.append(s)

        return cleaned

    def generate_answer(self, query, results, embedder, max_sentences=2):
        if not results:
            return "The answer is not available in the retrieved documents."

        context = " ".join(item["text"] for item in results)
        sentences = self.split_into_sentences(context)
        sentences = self.clean_sentences(sentences)

        if not sentences:
            return "The answer is not available in the retrieved documents."

        sentence_embeddings = embedder.encode(sentences)
        query_embedding = embedder.encode([query])

        scores = cosine_similarity(query_embedding, sentence_embeddings)[0]
        ranked_indices = scores.argsort()[::-1]

        selected = []
        seen = set()

        for idx in ranked_indices:
            sentence = sentences[idx]

            if sentence not in seen:
                selected.append(sentence)
                seen.add(sentence)

            if len(selected) == max_sentences:
                break

        if not selected:
            return "The answer is not available in the retrieved documents."

        return " ".join(selected)
