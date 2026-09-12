from app.hybrid_retriever import HybridRetriever
from app.context_builder import ContextBuilder
from app.answer_generator import AnswerGenerator

retriever = HybridRetriever()
context_builder = ContextBuilder()
answer_generator = AnswerGenerator()

queries = [
    "How does Flask dispatch an incoming HTTP request?",
    "How does Flask handle exceptions?",
    "How does Flask send a static file?",
    "How are user sessions saved in Flask?",
    "How does Flask register URL rules?",
]

for query in queries:
    print("\n" + "=" * 80)
    print("QUESTION:", query)
    print("=" * 80)

    results = retriever.search(
        query,
        top_k=5,
        candidate_k=10
    )

    context = context_builder.build(
        query,
        results
    )

    answer = answer_generator.generate(query, context)

    print("\nANSWER:")
    print(answer)