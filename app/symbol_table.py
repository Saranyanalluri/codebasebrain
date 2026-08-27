import ast
import json
from pathlib import Path


REPOSITORY_PATH = Path(
    "data/repositories/flask/src/flask"
)

OUTPUT_PATH = Path(
    "data/indexes/symbols.json"
)


def discover_symbols():

    symbols = []

    python_files = list(
        REPOSITORY_PATH.rglob("*.py")
    )

    for file_path in python_files:

        source_code = file_path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(source_code)

        relative_path = file_path.relative_to(
            REPOSITORY_PATH
        )

        for node in tree.body:

            # -------------------------
            # CLASS
            # -------------------------

            if isinstance(node, ast.ClassDef):

                class_record = {
                    "name": node.name,
                    "qualified_name": node.name,
                    "type": "class",
                    "file": str(relative_path),
                    "line": node.lineno,
                }

                symbols.append(class_record)

                # Methods
                for child in node.body:

                    if isinstance(
                        child,
                        (
                            ast.FunctionDef,
                            ast.AsyncFunctionDef,
                        ),
                    ):

                        method_record = {
                            "name": child.name,
                            "qualified_name": (
                                f"{node.name}.{child.name}"
                            ),
                            "type": "method",
                            "file": str(relative_path),
                            "line": child.lineno,
                        }

                        symbols.append(
                            method_record
                        )

            # -------------------------
            # TOP-LEVEL FUNCTION
            # -------------------------

            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                function_record = {
                    "name": node.name,
                    "qualified_name": node.name,
                    "type": "function",
                    "file": str(relative_path),
                    "line": node.lineno,
                }

                symbols.append(
                    function_record
                )

    return symbols


def save_symbols(symbols):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            symbols,
            file,
            indent=2
        )


def main():

    print("Discovering symbols...")

    symbols = discover_symbols()

    print(
        f"Discovered {len(symbols)} symbols."
    )

    save_symbols(symbols)

    print(
        f"Saved symbol table to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()