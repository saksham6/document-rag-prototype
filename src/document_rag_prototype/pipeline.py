from collections import Counter

from document_rag_prototype.chunker import build_chunk_index
from document_rag_prototype.config import DATA_FOLDER, MODEL_NAME, TOP_K
from document_rag_prototype.embedder import TextEmbedder
from document_rag_prototype.generator import AnswerGenerator
from document_rag_prototype.loader import load_documents
from document_rag_prototype.query_analyzer import analyze_query
from document_rag_prototype.reranker import ChunkReranker
from document_rag_prototype.search import semantic_search


def run_pipeline(query: str, source_filter: str | None = None, debug: bool = False) -> dict:
    print("Analyzing query...")
    query_info = analyze_query(query)
    print(f"Query type: {query_info['query_type']}")
    print(f"Query scope: {query_info['query_scope']}")

    print("Loading documents...")
    documents = load_documents(DATA_FOLDER)
    print(f"Loaded document entries: {len(documents)}")

    if source_filter:
        documents = [doc for doc in documents if doc["source"] == source_filter]
        print(f"Entries after source filter: {len(documents)}")

    if not documents:
        return {
            "query": query,
            "answer": "No matching documents were found for the given source filter.",
            "results": [],
        }

    print("Building chunk index...")
    chunk_index = build_chunk_index(documents)
    print(f"Chunks created: {len(chunk_index)}")

    if not chunk_index:
        return {
            "query": query,
            "answer": "No searchable content was found in the selected documents.",
            "results": [],
        }

    counts = Counter(chunk["content_type"] for chunk in chunk_index)
    print(f"Chunk content types: {dict(counts)}")

    if query_info["query_scope"] == "broad":
        search_top_k = 10
    else:
        search_top_k = TOP_K

    print("Loading embedder...")
    embedder = TextEmbedder(MODEL_NAME)

    print("Encoding chunks...")
    chunk_texts = [chunk["text"] for chunk in chunk_index]
    chunk_embeddings = embedder.encode(chunk_texts)

    print("Running semantic search...")
    search_results = semantic_search(
        query=query,
        chunk_index=chunk_index,
        chunk_embeddings=chunk_embeddings,
        embedder=embedder,
        top_k=search_top_k,
        source_filter=None,
        query_info=query_info,
    )
    print(f"Initial search results: {len(search_results)}")

    for i, item in enumerate(search_results[:10], start=1):
        preview = item["text"].replace("\n", " ")[:220]
        print(f"{i}. page={item['page']} | {item.get('content_type', 'mixed')} | score={item['score']:.3f}")
        print(f"   {preview}")

    if query_info["query_scope"] == "narrow":
        print("Loading reranker...")
        reranker = ChunkReranker()

        print("Reranking results...")
        final_results = reranker.rerank(query, search_results, top_k=search_top_k)
    else:
        print("Selecting broader evidence...")
        final_results = []
        used_pages = set()

        for item in search_results[:2]:
            final_results.append(item)
            used_pages.add(item.get("page"))

        for item in search_results[2:]:
            page = item.get("page")

            if page not in used_pages:
                final_results.append(item)
                used_pages.add(page)

            if len(final_results) == 4:
                break

        if len(final_results) < 4:
            for item in search_results:
                if item not in final_results:
                    final_results.append(item)

                if len(final_results) == 4:
                    break

    print("Generating answer...")
    generator = AnswerGenerator()
    answer = generator.generate_answer(
        query=query,
        results=final_results,
        embedder=embedder,
        query_info=query_info,
    )

    return {
        "query": query,
        "answer": answer,
        "results": final_results,
        "query_info": query_info,
    }


def main() -> None:
    query = input("Enter your question: ").strip()
    source_filter = input("Enter exact file name or press Enter for all documents: ").strip()

    if not query:
        print("Please enter a question.")
        return

    source_filter = source_filter or None
    output = run_pipeline(query, source_filter=source_filter)

    print("\nAnswer:")
    print(output["answer"])

    print("\nSources used:")
    if not output["results"]:
        print("- No results found")
        return

    for item in output["results"]:
        page = item["page"]
        page_text = f"page {page}" if page is not None else "no page"
        content_type = item.get("content_type", "mixed")
        print(f"- {item['source']} | {page_text} | chunk {item['chunk_id']} | {content_type}")


if __name__ == "__main__":
    main()