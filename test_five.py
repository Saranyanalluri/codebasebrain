from app.hybrid_retriever import HybridRetriever


retriever = HybridRetriever()


queries = [
    "How does Flask dispatch an incoming HTTP request?",
    "How does Flask handle exceptions?",
    "How does Flask send a static file?",
    "How are user sessions saved in Flask?",
    "How does Flask register URL rules?",
]


for query in queries:

    print("\n" + "=" * 70)
    print(query)
    print("=" * 70)

    results = retriever.search(
        query,
        top_k=5,
        candidate_k=10
    )

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"{rank}. "
            f"{result['qualified_name']}"
        )