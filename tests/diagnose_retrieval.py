from app.bm25_retriever import BM25Retriever
from app.semantic_retriever import SemanticRetriever
import json


DOCUMENTS_PATH = "data/indexes/code_documents.json"


def show_results(title, results, expected):
    print(f"\n--- {title} ---")

    for rank, result in enumerate(results, start=1):
        marker = "  <-- EXPECTED" if result.qualified_name == expected else ""

        print(
            f"{rank}. "
            f"{result.qualified_name} "
            f"| score={result.score:.4f}"
            f"{marker}"
        )


def main():
    with open(DOCUMENTS_PATH, "r", encoding="utf-8") as file:
        documents = json.load(file)

    bm25 = BM25Retriever(documents)
    semantic = SemanticRetriever(DOCUMENTS_PATH)

    test_cases = [
        (
            "How are user sessions saved in Flask?",
            "SecureCookieSessionInterface.save_session",
        ),
        (
            "How does Flask register URL rules?",
            "App.add_url_rule",
        ),
    ]

    for query, expected in test_cases:
        print("\n" + "=" * 70)
        print(f"QUERY: {query}")
        print(f"EXPECTED: {expected}")

        bm25_results = bm25.search(query, top_k=10)
        semantic_results = semantic.search(query, top_k=10)

        show_results("BM25", bm25_results, expected)
        show_results("SEMANTIC", semantic_results, expected)


if __name__ == "__main__":
    main()
