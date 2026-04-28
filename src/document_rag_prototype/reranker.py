from sentence_transformers import CrossEncoder


class ChunkReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, results: list[dict], top_k: int | None = None) -> list[dict]:
        if not results:
            return []

        pairs = [(query, item["text"]) for item in results]
        scores = self.model.predict(pairs)

        reranked = []

        for item, score in zip(results, scores):
            updated_item = item.copy()
            updated_item["rerank_score"] = float(score)
            reranked.append(updated_item)

        reranked.sort(key=lambda item: item["rerank_score"], reverse=True)

        if top_k is not None:
            reranked = reranked[:top_k]

        return reranked