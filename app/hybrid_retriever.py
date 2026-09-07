import json
from pathlib import Path

from sentence_transformers import CrossEncoder

from app.bm25_retriever import BM25Retriever
from app.semantic_retriever import SemanticRetriever
from app.graph_retriever import GraphRetriever


DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)


class HybridRetriever:

    def __init__(self):

        # Load code documents
        with open(
            DOCUMENTS_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            self.documents = json.load(file)

        # Initialize BM25 retriever
        self.bm25 = BM25Retriever(
            self.documents
        )

        # Initialize semantic retriever
        self.semantic = SemanticRetriever(
            DOCUMENTS_PATH
        )

        # Initialize graph retriever
        self.graph = GraphRetriever()

        # Initialize Cross-Encoder reranker
        self.reranker = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

    def search(
        self,
        query,
        top_k=5,
        candidate_k=10,
        rrf_k=60
    ):

        # --------------------------------------------------
        # 1. BM25 retrieval
        # --------------------------------------------------

        bm25_results = self.bm25.search(
            query,
            top_k=candidate_k
        )

        # --------------------------------------------------
        # 2. Semantic retrieval
        # --------------------------------------------------

        semantic_results = self.semantic.search(
            query,
            top_k=candidate_k
        )

        # --------------------------------------------------
        # 3. Select seeds for graph retrieval
        # --------------------------------------------------

        graph_seed_names = list(
            {
                result.qualified_name
                for result in (
                    bm25_results + semantic_results
                )
            }
        )

        # --------------------------------------------------
        # 4. Graph retrieval
        # --------------------------------------------------

        graph_results = self.graph.search(
            graph_seed_names,
            top_k=candidate_k
        )

        # --------------------------------------------------
        # 5. Map qualified names to document IDs
        # --------------------------------------------------

        document_id_by_name = {
            document["qualified_name"]: document["id"]
            for document in self.documents
        }

        # --------------------------------------------------
        # 6. Reciprocal Rank Fusion
        # --------------------------------------------------

        fused = {}

        # BM25 contribution
        for rank, result in enumerate(
            bm25_results,
            start=1
        ):

            document_id = result.document_id

            fused.setdefault(
                document_id,
                {
                    "result": result,
                    "rrf_score": 0.0
                }
            )

            fused[document_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

        # Semantic contribution
        for rank, result in enumerate(
            semantic_results,
            start=1
        ):

            document_id = result.document_id

            if document_id not in fused:

                fused[document_id] = {
                    "result": result,
                    "rrf_score": 0.0
                }

            fused[document_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

        # Graph contribution
        for rank, result in enumerate(
            graph_results,
            start=1
        ):

            document_id = document_id_by_name.get(
                result["qualified_name"]
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
                    "rrf_score": 0.0
                }

            fused[document_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

        # --------------------------------------------------
        # 7. First-stage ranking using RRF
        # --------------------------------------------------

        ranked = sorted(
            fused.values(),
            key=lambda item: item["rrf_score"],
            reverse=True
        )

        # Keep the best candidates for reranking
        candidates = ranked[:candidate_k]

        # --------------------------------------------------
        # 8. Build query-document pairs
        # --------------------------------------------------

        pairs = []

        for item in candidates:

            document = self.documents[
                item["result"].document_id
            ]

            pairs.append(
                (
                    query,
                    document["text"]
                )
            )

        # --------------------------------------------------
        # 9. Cross-Encoder reranking
        # --------------------------------------------------

        rerank_scores = self.reranker.predict(
            pairs
        )

        # Attach reranking scores
        for item, score in zip(
            candidates,
            rerank_scores
        ):

            item["rerank_score"] = float(score)

        # --------------------------------------------------
        # 10. Final ranking
        # --------------------------------------------------

        reranked = sorted(
            candidates,
            key=lambda item: item["rerank_score"],
            reverse=True
        )

        # --------------------------------------------------
        # 11. Return final results
        # --------------------------------------------------

        return [
            {
                "document_id": item["result"].document_id,
                "qualified_name": item["result"].qualified_name,
                "file": item["result"].file,
                "line": item["result"].line,
                "rrf_score": item["rrf_score"],
                "rerank_score": item["rerank_score"],
                "source": item["result"].source,
            }
            for item in reranked[:top_k]
        ]


# ----------------------------------------------------------
# Test the hybrid retriever
# ----------------------------------------------------------

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
            f"| Rerank={result['rerank_score']:.4f} "
            f"| {result['file']}:{result['line']}"
        )