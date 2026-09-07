import json
from pathlib import Path

from app.bm25_retriever import BM25Retriever
from app.semantic_retriever import SemanticRetriever
from app.graph_retriever import GraphRetriever


DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)


class HybridRetriever:

    def __init__(self):

        with open(
            DOCUMENTS_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            self.documents = json.load(file)

        self.bm25 = BM25Retriever(
            self.documents
        )

        self.semantic = SemanticRetriever(
            DOCUMENTS_PATH
        )

        self.graph = GraphRetriever()

    def search(
        self,
        query,
        top_k=5,
        candidate_k=10,
        rrf_k=60
    ):

        bm25_results = self.bm25.search(
            query,
            top_k=candidate_k
        )

        semantic_results = self.semantic.search(
            query,
            top_k=candidate_k
        )
        graph_seed_names = list(
            {
                result.qualified_name
                for result in (
                    bm25_results + semantic_results
                )
            }
        )

        graph_results = self.graph.search(
            graph_seed_names,
            top_k=candidate_k
        )

        fused = {}

        for rank, result in enumerate(
            bm25_results,
            start=1
        ):
            document_id = result.document_id

            fused.setdefault(
                document_id,
                {
                    "result": result,
                    "rrf_score": 0.0,
                }
            )

            fused[document_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

        for rank, result in enumerate(
            semantic_results,
            start=1
        ):
            document_id = result.document_id

            if document_id not in fused:
                fused[document_id] = {
                    "result": result,
                    "rrf_score": 0.0,
                }

            fused[document_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

            for rank, result in enumerate(
                graph_results,
                start=1
            ):
                document_id = next(
                    (
                    document["id"]
                    for document in self.documents
                    if document["qualified_name"]
                    == result["qualified_name"]
                    ),
                    None
                )

                if document_id is None:
                    continue

                if document_id not in fused:
                    fused[document_id] = {
                        "result": type(
                            "GraphResult",
                        (),
                        {
                            "document_id": document_id,
                            "qualified_name": result[
                                "qualified_name"
                            ],
                            "file": result["file"],
                            "line": result["line"],
                            "source": "graph",
                        }
                    )(),
                    "rrf_score": 0.0,
                }

            fused[document_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )
        ranked = sorted(
            fused.values(),
            key=lambda item: item["rrf_score"],
            reverse=True
        )

        return [
            {
                "document_id": item["result"].document_id,
                "qualified_name": item["result"].qualified_name,
                "file": item["result"].file,
                "line": item["result"].line,
                "rrf_score": item["rrf_score"],
                "source": item["result"].source,
            }
            for item in ranked[:top_k]
        ]


if __name__ == "__main__":

    retriever = HybridRetriever()

    query = (
        "how does Flask dispatch "
        "an incoming HTTP request"
    )

    results = retriever.search(
        query,
        top_k=10
    )

    print("\nHybrid Results:\n")

    for rank, result in enumerate(
        results,
        start=1
    ):
        print(
            f"{rank}. "
            f"{result['qualified_name']} "
            f"| RRF={result['rrf_score']:.6f} "
            f"| {result['file']}:{result['line']}"
        )