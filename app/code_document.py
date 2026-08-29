import json
from pathlib import Path


REPOSITORY_PATH = Path(
    "data/repositories/flask/src/flask"
)

SYMBOLS_PATH = Path(
    "data/indexes/symbols.json"
)

OUTPUT_PATH = Path(
    "data/indexes/code_documents.json"
)


def load_symbols():

    with SYMBOLS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def read_symbol_source(symbol):

    file_path = (
        REPOSITORY_PATH
        / symbol["file"]
    )

    lines = file_path.read_text(
        encoding="utf-8"
    ).splitlines()

    start = symbol["line"] - 1

    # Initially take a reasonable
    # context window.
    end = min(
        start + 80,
        len(lines)
    )

    return "\n".join(
        lines[start:end]
    )


def build_documents():

    symbols = load_symbols()

    documents = []

    for index, symbol in enumerate(symbols):

        try:

            source = read_symbol_source(
                symbol
            )

        except Exception as error:

            print(
                f"Skipping "
                f"{symbol['qualified_name']}: "
                f"{error}"
            )

            continue

        document = {

            "id": index,

            "qualified_name":
                symbol["qualified_name"],

            "name":
                symbol["name"],

            "type":
                symbol["type"],

            "file":
                symbol["file"],

            "line":
                symbol["line"],

            "text": source,
        }

        documents.append(document)

    return documents


def save_documents(documents):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            documents,
            file,
            indent=2
        )


def main():

    print("Building code documents...")

    documents = build_documents()

    print(
        f"Documents created: "
        f"{len(documents)}"
    )

    save_documents(documents)

    print(
        f"Saved documents to: "
        f"{OUTPUT_PATH}"
    )

    print("\nFirst document:\n")

    if documents:

        document = documents[0]

        print(
            f"ID: {document['id']}"
        )

        print(
            f"Symbol: "
            f"{document['qualified_name']}"
        )

        print(
            f"File: "
            f"{document['file']}"
        )

        print(
            f"Line: "
            f"{document['line']}"
        )


if __name__ == "__main__":
    main()