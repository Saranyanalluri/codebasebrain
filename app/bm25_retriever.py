import json
import re
from pathlib import Path
from app.retrieval import RetrievalResult

from rank_bm25 import BM25Okapi


DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)


def load_documents():

    with DOCUMENTS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def tokenize(text):

    text = text.lower()

    # Keep the original identifier.
    tokens = re.findall(
        r"[a-zA-Z_][a-zA-Z0-9_]*",
        text
    )

    # Also add identifier components.
    expanded_tokens = []

    for token in tokens:
        expanded_tokens.append(token)

        if "_" in token:
            expanded_tokens.extend(
                part
                for part in token.split("_")
                if part
            )

    return expanded_tokens


class BM25Retriever:

    def __init__(self, documents):

        self.documents = documents

        corpus = [
            tokenize(
                self.build_search_text(doc)
            )
            for doc in documents
        ]

        self.bm25 = BM25Okapi(corpus)

    def build_search_text(self, document):

        return " ".join([
            document["qualified_name"],
            document["name"],
            document["file"],
            document["type"],
            document["text"],
        ])

    def search(self, query, top_k=5):

        query_tokens = tokenize(query)

        scores = self.bm25.get_scores(
            query_tokens
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )

        results = []

        for index in ranked_indices[:top_k]:

            document = self.documents[index]

            results.append(
                RetrievalResult(
                    document_id=document["id"],
                    qualified_name=document["qualified_name"],
                    file=document["file"],
                    line=document["line"],
                    score=float(scores[index]),
                    source=document["text"],
                    retriever="bm25",
                )
            )

        return results


def main():

    print("Loading code documents...")

    documents = load_documents()

    print(
        f"Loaded {len(documents)} documents."
    )

    retriever = BM25Retriever(
        documents
    )

    query = input(
        "\nEnter a search query: "
    )

    results = retriever.search(
        query,
        top_k=5
    )

    print(
        "\nTop results:\n"
    )

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"{rank}. "
            f"{result.qualified_name} "
            f"| score={result.score:.4f} "
            f"| {result.file}:"
            f"{result.line}"
        )
        print(
            result.source[:500]
        )

        print("-" * 60)


if __name__ == "__main__":
    main()