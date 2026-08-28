import ast
import json
from pathlib import Path

RESOLVED_CALLS_PATH = Path(
    "data/indexes/resolved_calls.json"
)
def load_resolved_calls():

    with RESOLVED_CALLS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)
REPOSITORY_PATH = Path(
    "data/repositories/flask/src/flask"
)

SYMBOLS_PATH = Path(
    "data/indexes/symbols.json"
)

GRAPH_PATH = Path(
    "data/indexes/code_graph.json"
)


def load_symbols():
    with SYMBOLS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def build_symbol_lookup(symbols):
    lookup = {}

    for symbol in symbols:
        lookup[symbol["qualified_name"]] = symbol

    return lookup


def build_graph(symbols):

    nodes = symbols.copy()
    edges = []

    lookup = build_symbol_lookup(symbols)

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

            if not isinstance(
                node,
                ast.ClassDef
            ):
                continue

            class_name = node.name

            # -------------------------
            # DEFINES relationships
            # -------------------------

            for child in node.body:

                if not isinstance(
                    child,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    continue

                method_name = (
                    f"{class_name}.{child.name}"
                )

                if method_name in lookup:

                    edges.append({
                        "source": class_name,
                        "target": method_name,
                        "type": "DEFINES",
                        "file": str(relative_path),
                        "line": child.lineno,
                    })

            # -------------------------
            # INHERITS relationships
            # -------------------------

            for base in node.bases:

                base_name = ast.unparse(base)

                edges.append({
                    "source": class_name,
                    "target": base_name,
                    "type": "INHERITS",
                    "file": str(relative_path),
                    "line": node.lineno,
                })

    return {
        "nodes": nodes,
        "edges": edges,
    }


def save_graph(graph):

    GRAPH_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with GRAPH_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            graph,
            file,
            indent=2
        )


def main():

    print("Loading symbol table...")

    symbols = load_symbols()

    print(
        f"Loaded {len(symbols)} symbols."
    )

    print("Building graph...")

    graph = build_graph(symbols)
    resolved_calls = load_resolved_calls()

    graph["edges"].extend(
        resolved_calls
    )

    print(
        f"Nodes: {len(graph['nodes'])}"
    )

    print(
        f"Edges: {len(graph['edges'])}"
    )

    save_graph(graph)

    print(
        f"Saved graph to: {GRAPH_PATH}"
    )


if __name__ == "__main__":
    main()