from app.hybrid_retriever import HybridRetriever
from app.context_builder import ContextBuilder
from app.answer_generator import AnswerGenerator


def run_pipeline(query):
    print("=" * 70)
    print("CODEBASEBRAIN")
    print("=" * 70)

    # ---------------------------------------------------------
    # Step 1: Hybrid Retrieval
    # ---------------------------------------------------------

    print("\n[1] Searching repository...")

    retriever = HybridRetriever()

    results = retriever.search(
        query,
        top_k=5,
        candidate_k=20,
    )

    print(f"Retrieved {len(results)} relevant code components.")

    # ---------------------------------------------------------
    # Step 2: Build Context
    # ---------------------------------------------------------

    print("\n[2] Building code context...")

    context_builder = ContextBuilder()

    context = context_builder.build(
        query,
        results,
        max_results=5,
    )

    print(f"Context contains {len(context['results'])} results.")

    # ---------------------------------------------------------
    # Step 3: Generate Answer
    # ---------------------------------------------------------

    print("\n[3] Analyzing code...")

    generator = AnswerGenerator()

    answer = generator.generate(
        query,
        context,
    )

    # ---------------------------------------------------------
    # Step 4: Display Answer
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("CODEBASEBRAIN ANSWER")
    print("=" * 70)

    print("\n" + answer)

    print("\n" + "=" * 70)


def main():
    query = input("\nAsk a question about the repository: ").strip()

    if not query:
        print("Please enter a question.")
        return

    run_pipeline(query)


if __name__ == "__main__":
    main()