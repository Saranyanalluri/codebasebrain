import ast
import json
from pathlib import Path


REPOSITORY_PATH = Path(
    "data/repositories/flask/src/flask"
)

SYMBOLS_PATH = Path(
    "data/indexes/symbols.json"
)

GRAPH_PATH = Path(
    "data/indexes/code_graph.json"
)

OUTPUT_PATH = Path(
    "data/indexes/resolved_calls.json"
)


class CallVisitor(ast.NodeVisitor):

    def __init__(self):
        self.calls = []
        self.current_class = None
        self.current_function = None

    def visit_ClassDef(self, node):

        previous_class = self.current_class

        self.current_class = node.name

        self.generic_visit(node)

        self.current_class = previous_class

    def visit_FunctionDef(self, node):

        self.visit_function(node)

    def visit_AsyncFunctionDef(self, node):

        self.visit_function(node)

    def visit_function(self, node):

        previous_function = self.current_function

        if self.current_class:
            self.current_function = (
                f"{self.current_class}.{node.name}"
            )
        else:
            self.current_function = node.name

        self.generic_visit(node)

        self.current_function = previous_function

    def visit_Call(self, node):

        callee = self.get_call_name(node.func)

        if callee and self.current_function:

            self.calls.append({
                "caller": self.current_function,
                "callee": callee,
                "line": node.lineno,
            })

        self.generic_visit(node)

    def get_call_name(self, node):

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):

            parts = []

            current = node

            while isinstance(
                current,
                ast.Attribute
            ):
                parts.append(current.attr)
                current = current.value

            if isinstance(
                current,
                ast.Name
            ):
                parts.append(current.id)

            parts.reverse()

            return ".".join(parts)

        return None


def load_symbols():

    with SYMBOLS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def build_method_lookup(symbols):

    methods = set()

    for symbol in symbols:

        if symbol["type"] == "method":
            methods.add(
                symbol["qualified_name"]
            )

    return methods


def build_inheritance_lookup():

    with GRAPH_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        graph = json.load(file)

    inheritance = {}

    for edge in graph["edges"]:

        if edge["type"] != "INHERITS":
            continue

        child = edge["source"]
        parent = edge["target"]

        inheritance.setdefault(
            child,
            []
        ).append(parent)

    return inheritance


def resolve_self_call(
    caller,
    callee,
    method_lookup,
    inheritance
):

    if not callee.startswith("self."):
        return None

    if "." not in caller:
        return None

    class_name = caller.split(".")[0]

    method_name = callee[
        len("self.") :
    ]

    # First: current class
    candidate = (
        f"{class_name}.{method_name}"
    )

    if candidate in method_lookup:
        return candidate

    # Second: inherited methods
    visited = set()

    queue = list(
        inheritance.get(
            class_name,
            []
        )
    )

    while queue:

        parent = queue.pop(0)

        if parent in visited:
            continue

        visited.add(parent)

        candidate = (
            f"{parent}.{method_name}"
        )

        if candidate in method_lookup:
            return candidate

        queue.extend(
            inheritance.get(
                parent,
                []
            )
        )

    return None


def analyze_repository():

    all_calls = []

    python_files = list(
        REPOSITORY_PATH.rglob("*.py")
    )

    for file_path in python_files:

        calls = CallVisitor()

        source_code = file_path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(source_code)

        calls.visit(tree)

        all_calls.extend(
            calls.calls
        )

    return all_calls


def resolve_calls(
    calls,
    method_lookup,
    inheritance
):

    resolved = []

    for call in calls:

        target = resolve_self_call(
            call["caller"],
            call["callee"],
            method_lookup,
            inheritance
        )

        if target:

            resolved.append({
                "source": call["caller"],
                "target": target,
                "type": "CALLS",
                "line": call["line"],
            })

    return resolved


def save_results(results):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=2
        )


def main():

    print("Loading symbols...")

    symbols = load_symbols()

    method_lookup = build_method_lookup(
        symbols
    )

    print(
        f"Methods available: "
        f"{len(method_lookup)}"
    )

    print("Loading inheritance...")

    inheritance = (
        build_inheritance_lookup()
    )

    print("Analyzing repository calls...")

    calls = analyze_repository()

    print(
        f"Raw calls found: {len(calls)}"
    )

    print("Resolving calls...")

    resolved = resolve_calls(
        calls,
        method_lookup,
        inheritance
    )

    print(
        f"Resolved internal calls: "
        f"{len(resolved)}"
    )

    save_results(resolved)

    print(
        f"Saved resolved calls to: "
        f"{OUTPUT_PATH}"
    )

    print("\nFirst 30 resolved calls:\n")

    for edge in resolved[:30]:

        print(
            f"{edge['source']} "
            f"→ CALLS → "
            f"{edge['target']} "
            f"(line {edge['line']})"
        )


if __name__ == "__main__":
    main()