import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from app.retrieval import RetrievalResult


DOCUMENTS_PATH = Path("data/indexes/code_documents.json")


class SemanticRetriever:
    def __init__(self, documents_path=DOCUMENTS_PATH):
        with open(documents_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
        )

        self.texts = [
            self._build_search_text(document)
            for document in self.documents
        ]

        self.embeddings = self.model.encode(
            self.texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

    def _build_search_text(self, document):
        return (
            f"{document['qualified_name']} "
            f"{document['name']} "
            f"{document['type']} "
            f"{document['file']} "
            f"{document['text']}"
        )

    def search(self, query, top_k=5):
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
        )[0]

        scores = np.dot(self.embeddings, query_embedding)

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []

        for index in top_indices:
            document = self.documents[index]

            results.append(
                RetrievalResult(
                    document_id=document["id"],
                    qualified_name=document["qualified_name"],
                    file=document["file"],
                    line=document["line"],
                    score=float(scores[index]),
                    source="semantic",
                    retriever="MiniLM",
                )
            )

        return results


if __name__ == "__main__":
    retriever = SemanticRetriever()

    queries = [
        "how does Flask process a request",
        "send a static file",
        "manage user sessions",
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        results = retriever.search(query, top_k=5)

        for rank, result in enumerate(results, 1):
            print(
                f"{rank}. "
                f"{result.qualified_name} "
                f"({result.score:.4f}) "
                f"{result.file}:{result.line}"
            )