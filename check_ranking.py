from app.hybrid_retriever import HybridRetriever

r = HybridRetriever()

results = r.search(
    "How does Flask register URL rules?",
    top_k=10,
    candidate_k=20
)

for i, x in enumerate(results, 1):
    print(
        f"{i}. {x['qualified_name']} "
        f"| Final={x['final_score']:.6f} "
        f"| RRF={x['rrf_score']:.6f} "
        f"| ID={x['identifier_score']} "
        f"| Source={x['source']}"
    )