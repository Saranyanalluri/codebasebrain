from dataclasses import dataclass


@dataclass
class RetrievalResult:

    document_id: int

    qualified_name: str

    file: str

    line: int

    score: float

    source: str

    retriever: str