from app.hybrid_retriever import HybridRetriever
from app.context_builder import ContextBuilder
from app.answer_generator import AnswerGenerator


def main():
    query = "How does Flask register URL rules?"

    print("=" * 70)
    print("CODEBASEBRAIN END-TO-END PIPELINE")
    print("=" * 70)

    # ---------------------------------------------------------
    # Step 1: Retrieve relevant code
    # ---------------------------------------------------------

    print("\n[1] Running hybrid retrieval...")

    retriever = HybridRetriever()

    results = retriever.search(
        query,
        top_k=5,
        candidate_k=20,
    )

    print(f"Retrieved {len(results)} results.")

    # ---------------------------------------------------------
    # Step 2: Build structured context
    # ---------------------------------------------------------

    print("\n[2] Building context...")

    context_builder = ContextBuilder()

    context = context_builder.build(
        query,
        results,
        max_results=5,
    )

    print(f"Context contains {len(context['results'])} results.")

    # ---------------------------------------------------------
    # Step 3: Generate answer
    # ---------------------------------------------------------

    print("\n[3] Generating answer...")

    generator = AnswerGenerator()

    answer = generator.generate(
        query,
        context,
    )

    # ---------------------------------------------------------
    # Step 4: Display final answer
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)

    print("\n" + answer)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()