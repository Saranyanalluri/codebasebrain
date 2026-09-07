import json
import time

from app.hybrid_retriever import HybridRetriever


EVALUATION_FILE = "tests/evaluation_queries.json"


def reciprocal_rank(results, expected):
    for rank, result in enumerate(results, start=1):
        if result["qualified_name"] == expected:
            return 1 / rank
    return 0.0


def main():
    with open(EVALUATION_FILE, "r", encoding="utf-8") as file:
        queries = json.load(file)

    retriever = HybridRetriever()

    total_reciprocal_rank = 0.0
    correct_at_5 = 0
    total_latency = 0.0

    print("\n===== CodebaseBrain Retrieval Evaluation =====\n")

    for item in queries:
        query = item["query"]
        expected = item["expected"]

        start = time.perf_counter()

        results = retriever.search(
            query,
            top_k=5,
            candidate_k=20
        )

        latency = time.perf_counter() - start
        total_latency += latency

        rank = None

        for position, result in enumerate(results, start=1):
            if result["qualified_name"] == expected:
                rank = position
                break

        if rank is not None:
            correct_at_5 += 1
            rr = 1 / rank
        else:
            rr = 0.0

        total_reciprocal_rank += rr

        print(f"Query:    {query}")
        print(f"Expected: {expected}")

        if rank:
            print(f"Found at: Rank {rank}")
        else:
            print("Found at: Not in Top 5")

        print(f"Latency:  {latency:.3f} seconds")
        print()

    total_queries = len(queries)

    recall_at_5 = correct_at_5 / total_queries
    mrr = total_reciprocal_rank / total_queries
    average_latency = total_latency / total_queries

    print("===== Evaluation Summary =====")
    print(f"Queries:          {total_queries}")
    print(f"Recall@5:         {recall_at_5:.2%}")
    print(f"MRR:              {mrr:.4f}")
    print(f"Average Latency:  {average_latency:.3f} seconds")


if __name__ == "__main__":
    main()