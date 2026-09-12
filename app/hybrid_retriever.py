import json
import re
from pathlib import Path

from app.bm25_retriever import BM25Retriever
from app.semantic_retriever import SemanticRetriever
from app.graph_retriever import GraphRetriever
from app.query_expander import expand_query
from app.identifier_matcher import identifier_match_score
from app.explanation_engine import ExplanationEngine


DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)


class HybridRetriever:

    def __init__(self):

        # --------------------------------------------------
        # Load code documents
        # --------------------------------------------------

        with open(
            DOCUMENTS_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            self.documents = json.load(file)

        # --------------------------------------------------
        # Initialize retrievers
        # --------------------------------------------------

        self.bm25 = BM25Retriever(
            self.documents
        )

        self.semantic = SemanticRetriever(
            DOCUMENTS_PATH
        )

        self.graph = GraphRetriever()

        self.explanation_engine = (
            ExplanationEngine()
        )

        # --------------------------------------------------
        # Document lookup
        # --------------------------------------------------

        self.document_by_id = {
            document["id"]: document
            for document in self.documents
        }

        self.document_id_by_name = {
            document["qualified_name"]: document["id"]
            for document in self.documents
        }


    # ======================================================
    # Query tokenization
    # ======================================================

    @staticmethod
    def _tokenize(text):

        text = text.lower()

        return set(
            re.findall(
                r"[a-zA-Z_][a-zA-Z0-9_]*",
                text
            )
        )


    # ======================================================
    # Convert snake_case identifiers into words
    # ======================================================

    @staticmethod
    def _split_identifier(identifier):

        identifier = identifier.lower()

        parts = []

        for token in identifier.split("."):

            parts.append(token)

            if "_" in token:

                parts.extend(
                    part
                    for part in token.split("_")
                    if part
                )

        return set(parts)


    # ======================================================
    # Method / entity relevance
    # ======================================================

    def _name_match_score(
        self,
        query,
        qualified_name
    ):

        query_tokens = self._tokenize(
            query
        )

        name_tokens = self._split_identifier(
            qualified_name
        )

        if not query_tokens or not name_tokens:
            return 0.0

        # Ignore very common English words.
        stop_words = {
            "how",
            "does",
            "do",
            "the",
            "a",
            "an",
            "is",
            "are",
            "in",
            "of",
            "to",
            "for",
            "with",
            "and",
            "on",
            "from",
            "flask"
        }

        meaningful_query_tokens = (
            query_tokens - stop_words
        )

        if not meaningful_query_tokens:
            return 0.0

        overlap = (
            meaningful_query_tokens
            & name_tokens
        )

        if not overlap:
            return 0.0

        return (
            len(overlap)
            / len(meaningful_query_tokens)
        )


    # ======================================================
    # Detect direct class/entity mention
    # ======================================================

    def _entity_match_score(
        self,
        query,
        qualified_name
    ):

        query_tokens = self._tokenize(
            query
        )

        name_parts = qualified_name.split(".")

        if not name_parts:
            return 0.0

        class_name = name_parts[0].lower()

        if class_name in query_tokens:
            return 1.0

        return 0.0


    # ======================================================
    # Search
    # ======================================================

    def search(
        self,
        query,
        top_k=5,
        candidate_k=10,
        rrf_k=60,
        identifier_weight=0.02
    ):

        # --------------------------------------------------
        # 1. Expand query
        # --------------------------------------------------

        expanded_query = expand_query(
            query
        )


        # --------------------------------------------------
        # 2. BM25
        # --------------------------------------------------

        bm25_results = self.bm25.search(
            expanded_query,
            top_k=candidate_k
        )


        # --------------------------------------------------
        # 3. Semantic retrieval
        # --------------------------------------------------

        semantic_results = self.semantic.search(
            query,
            top_k=candidate_k
        )


        # --------------------------------------------------
        # 4. Graph seeds
        # --------------------------------------------------

        graph_seed_names = list(
            {
                result.qualified_name
                for result in (
                    bm25_results
                    + semantic_results
                )
            }
        )


        # --------------------------------------------------
        # 5. Graph retrieval
        # --------------------------------------------------

        graph_results = self.graph.search(
            graph_seed_names,
            top_k=candidate_k
        )


        # --------------------------------------------------
        # 6. Fusion container
        # --------------------------------------------------

        fused = {}


        # --------------------------------------------------
        # Helper
        # --------------------------------------------------

        def ensure_item(
            document_id,
            result
        ):

            if document_id not in fused:

                fused[document_id] = {
                    "result": result,
                    "rrf_score": 0.0,
                    "sources": set(),
                    "evidence": {}
                }


        # --------------------------------------------------
        # 7. BM25 contribution
        #
        # BM25 is strongest for exact code identifiers.
        # --------------------------------------------------

        for rank, result in enumerate(
            bm25_results,
            start=1
        ):

            document_id = result.document_id

            ensure_item(
                document_id,
                result
            )

            contribution = (
                1.0
                / (rrf_k + rank)
            )

            fused[
                document_id
            ]["rrf_score"] += contribution

            fused[
                document_id
            ]["sources"].add(
                "bm25"
            )

            fused[
                document_id
            ]["evidence"]["bm25"] = {
                "rank": rank,
                "rrf_contribution": contribution
            }


        # --------------------------------------------------
        # 8. Semantic contribution
        #
        # Semantic retrieval gets equal direct-search
        # importance to BM25.
        # --------------------------------------------------

        for rank, result in enumerate(
            semantic_results,
            start=1
        ):

            document_id = result.document_id

            ensure_item(
                document_id,
                result
            )

            contribution = (
                1.0
                / (rrf_k + rank)
            )

            fused[
                document_id
            ]["rrf_score"] += contribution

            fused[
                document_id
            ]["sources"].add(
                "semantic"
            )

            fused[
                document_id
            ]["evidence"]["semantic"] = {
                "rank": rank,
                "rrf_contribution": contribution
            }


        # --------------------------------------------------
        # 9. Graph contribution
        #
        # Graph is supporting evidence.
        #
        # It should NOT be allowed to overpower direct
        # lexical / semantic retrieval.
        # --------------------------------------------------

        GRAPH_WEIGHT = 0.35

        for rank, result in enumerate(
            graph_results,
            start=1
        ):

            document_id = (
                self.document_id_by_name.get(
                    result["qualified_name"]
                )
            )

            if document_id is None:
                continue

            graph_result = type(
                "GraphResult",
                (),
                {
                    "document_id": document_id,
                    "qualified_name": result[
                        "qualified_name"
                    ],
                    "file": result["file"],
                    "line": result["line"],
                    "source": "graph"
                }
            )()

            ensure_item(
                document_id,
                graph_result
            )

            contribution = (
                GRAPH_WEIGHT
                * (
                    1.0
                    / (rrf_k + rank)
                )
            )

            fused[
                document_id
            ]["rrf_score"] += contribution

            fused[
                document_id
            ]["sources"].add(
                "graph"
            )

            fused[
                document_id
            ]["evidence"]["graph"] = {
                "rank": rank,
                "rrf_contribution": contribution,
                "graph_weight": GRAPH_WEIGHT
            }


        # --------------------------------------------------
        # 10. Additional relevance signals
        # --------------------------------------------------

        for item in fused.values():

            qualified_name = (
                item["result"].qualified_name
            )

            # ----------------------------------------------
            # Identifier matching
            # ----------------------------------------------

            identifier_score = (
                identifier_match_score(
                    expanded_query,
                    qualified_name
                )
            )

            item[
                "identifier_score"
            ] = identifier_score

            item[
                "evidence"
            ]["identifier"] = {
                "score": identifier_score
            }


            # ----------------------------------------------
            # Method/entity name overlap
            # ----------------------------------------------

            name_match_score = (
                self._name_match_score(
                    query,
                    qualified_name
                )
            )

            item[
                "name_match_score"
            ] = name_match_score

            item[
                "evidence"
            ]["name_match"] = {
                "score": name_match_score
            }


            # ----------------------------------------------
            # Direct entity/class match
            # ----------------------------------------------

            entity_match_score = (
                self._entity_match_score(
                    query,
                    qualified_name
                )
            )

            item[
                "entity_match_score"
            ] = entity_match_score

            item[
                "evidence"
            ]["entity_match"] = {
                "score": entity_match_score
            }


            # ----------------------------------------------
            # Final score
            # ----------------------------------------------

            item[
                "final_score"
            ] = (
                item["rrf_score"]

                + (
                    identifier_weight
                    * identifier_score
                )

                + (
                    0.015
                    * name_match_score
                )

                + (
                    0.005
                    * entity_match_score
                )
            )


        # --------------------------------------------------
        # 11. Final ranking
        # --------------------------------------------------

        ranked = sorted(
            fused.values(),
            key=lambda item: (
                item["final_score"],
                item["rrf_score"]
            ),
            reverse=True
        )


        # --------------------------------------------------
        # 12. Build final results
        # --------------------------------------------------

        results = []

        for item in ranked[:top_k]:

            result = {

                "document_id":
                    item["result"].document_id,

                "qualified_name":
                    item["result"].qualified_name,

                "file":
                    item["result"].file,

                "line":
                    item["result"].line,

                "rrf_score":
                    item["rrf_score"],

                "identifier_score":
                    item["identifier_score"],

                "name_match_score":
                    item["name_match_score"],

                "entity_match_score":
                    item["entity_match_score"],

                "final_score":
                    item["final_score"],

                "rerank_score":
                    None,

                "sources":
                    sorted(
                        item["sources"]
                    ),

                "evidence":
                    item["evidence"]
            }


            # --------------------------------------------------
            # Explanation
            # --------------------------------------------------

            result["explanation"] = (
                self.explanation_engine.explain(
                    result
                )
            )

            results.append(
                result
            )


        return results


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    retriever = HybridRetriever()

    query = (
        "How does Flask register URL rules?"
    )

    results = retriever.search(
        query,
        top_k=5
    )

    print(
        "\nCodebaseBrain Hybrid Search\n"
    )

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"{rank}. "
            f"{result['qualified_name']}"
        )

        print(
            f"   Sources: "
            f"{', '.join(result['sources'])}"
        )

        print(
            f"   RRF: "
            f"{result['rrf_score']:.6f}"
        )

        print(
            f"   Identifier: "
            f"{result['identifier_score']:.3f}"
        )

        print(
            f"   Name Match: "
            f"{result['name_match_score']:.3f}"
        )

        print(
            f"   Entity Match: "
            f"{result['entity_match_score']:.3f}"
        )

        print(
            f"   Final: "
            f"{result['final_score']:.6f}"
        )

        print(
            f"   Location: "
            f"{result['file']}:{result['line']}"
        )

        print(
            "   Why relevant:"
        )

        for explanation in result[
            "explanation"
        ]:

            print(
                f"      ✓ {explanation}"
            )

        print()