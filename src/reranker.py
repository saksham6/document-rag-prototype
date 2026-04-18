from sentence_transformers import CrossEncoder


class ChunkReranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query, results, top_k=None):
        if not results:
            return []

        pairs = [(query, item["text"]) for item in results]
        scores = self.model.predict(pairs)

        reranked = []
        for item, score in zip(results, scores):
            new_item = item.copy()
            new_item["rerank_score"] = float(score)
            reranked.append(new_item)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        if top_k is not None:
            reranked = reranked[:top_k]

        return reranked
