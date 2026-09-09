import json
from pathlib import Path


DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)


class ContextBuilder:
    """
    Builds structured context from retrieval results.

    The context is intended to be consumed later by
    an answer-generation model.
    """

    def __init__(
        self,
        documents_path=DOCUMENTS_PATH
    ):

        self.documents_path = Path(
            documents_path
        )

        with open(
            self.documents_path,
            "r",
            encoding="utf-8"
        ) as file:

            self.documents = json.load(file)

        # Fast document lookup
        self.documents_by_id = {
            document["id"]: document
            for document in self.documents
        }

    def build(
        self,
        query,
        results,
        max_results=5
    ):
        """
        Build a structured context object.

        Parameters
        ----------
        query:
            Original user query.

        results:
            Results returned by HybridRetriever.

        max_results:
            Maximum number of retrieved results
            to include in the context.
        """

        context_results = []

        for result in results[:max_results]:

            document_id = result.get(
                "document_id"
            )

            document = self.documents_by_id.get(
                document_id
            )

            if document is None:
                continue

            context_results.append({

                "qualified_name":
                    result.get(
                        "qualified_name"
                    ),

                "file":
                    result.get(
                        "file"
                    ),

                "line":
                    result.get(
                        "line"
                    ),

                "code":
                    document.get(
                        "text",
                        ""
                    ),

                "sources":
                    result.get(
                        "sources",
                        []
                    ),

                "evidence":
                    result.get(
                        "evidence",
                        {}
                    ),

                "explanation":
                    result.get(
                        "explanation",
                        []
                    ),

                "final_score":
                    result.get(
                        "final_score"
                    )
            })

        return {
            "query": query,
            "results": context_results
        }

    def format_for_llm(
        self,
        context
    ):
        """
        Convert structured retrieval context
        into a readable text representation.

        This will later become the input context
        for the answer-generation model.
        """

        sections = []

        sections.append(
            f"User Question:\n"
            f"{context['query']}"
        )

        sections.append(
            "\nRetrieved Code Context:"
        )

        for index, result in enumerate(
            context["results"],
            start=1
        ):

            sections.append(
                "\n"
                + "=" * 70
            )

            sections.append(
                f"Result {index}"
            )

            sections.append(
                f"Symbol: "
                f"{result['qualified_name']}"
            )

            sections.append(
                f"File: "
                f"{result['file']}"
            )

            sections.append(
                f"Line: "
                f"{result['line']}"
            )

            sections.append(
                f"Sources: "
                f"{', '.join(result['sources'])}"
            )

            sections.append(
                "\nCode:"
            )

            sections.append(
                result["code"]
            )

            sections.append(
                "\nWhy this result was retrieved:"
            )

            for explanation in (
                result["explanation"]
            ):

                sections.append(
                    f"- {explanation}"
                )

        return "\n".join(
            sections
        )


# ==========================================================
# Standalone test
# ==========================================================

if __name__ == "__main__":

    from app.hybrid_retriever import (
        HybridRetriever
    )

    query = (
        "How does Flask register URL rules?"
    )

    # Run hybrid retrieval
    retriever = HybridRetriever()

    results = retriever.search(
        query,
        top_k=5
    )

    # Build context
    builder = ContextBuilder()

    context = builder.build(
        query,
        results
    )

    # Display structured context
    print(
        "\nStructured Context\n"
    )

    print(
        json.dumps(
            context,
            indent=2,
            ensure_ascii=False
        )
    )

    # Display LLM-ready context
    print(
        "\n\nLLM-Ready Context\n"
    )

    formatted_context = (
        builder.format_for_llm(
            context
        )
    )

    print(
        formatted_context
    )