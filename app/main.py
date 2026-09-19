import sys

from app.hybrid_retriever import HybridRetriever
from app.context_builder import ContextBuilder
from app.llm_answer_generator import LLMAnswerGenerator


def run_pipeline(query, provider="mock"):
    print("=" * 70)
    print("CODEBASEBRAIN")
    print("=" * 70)

    print("\n[1] Searching repository...")

    retriever = HybridRetriever()

    results = retriever.search(
        query,
        top_k=5,
        candidate_k=20
    )

    print(
        f"Retrieved {len(results)} relevant code components."
    )

    print("\n[2] Building code context...")

    context_builder = ContextBuilder()

    context = context_builder.build(
        query,
        results,
        max_results=5
    )

    print(
        f"Context contains {len(context['results'])} results."
    )

    print(
        f"\n[3] Generating answer with {provider}..."
    )

    generator = LLMAnswerGenerator(provider)

    answer = generator.generate(
        query,
        context
    )

    print("\n" + "=" * 70)
    print("CODEBASEBRAIN ANSWER")
    print("=" * 70)

    print("\n" + answer)

    print("\n" + "=" * 70)


def main():

    query = input(
        "\nAsk a question about the repository: "
    ).strip()

    if not query:
        print("Please enter a question.")
        return

    # Default provider is now local.
    provider = "local"

    # Optional command-line provider.
    #
    # Examples:
    # python -m app.main local
    # python -m app.main mock
    # python -m app.main claude
    # python -m app.main openai

    if len(sys.argv) > 1:
        provider = sys.argv[1]

    run_pipeline(
        query,
        provider
    )


if __name__ == "__main__":
    main()