import ast
from pathlib import Path


PYTHON_FILE = Path(
    "data/repositories/flask/src/flask/app.py"
)


class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)

        elif isinstance(node.func, ast.Attribute):
            self.calls.append(ast.unparse(node.func))

        self.generic_visit(node)


def analyze_file():
    source_code = PYTHON_FILE.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source_code)

    print("CODE STRUCTURE\n")
    print(f"File: {PYTHON_FILE}\n")

    for node in tree.body:

        if isinstance(node, ast.ClassDef):
            print(f"CLASS: {node.name}")

            if node.bases:
                bases = [
                    ast.unparse(base)
                    for base in node.bases
                ]

                print(
                    f"  Inherits from: {', '.join(bases)}"
                )

            for child in node.body:

                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    print(f"\n  METHOD: {child.name}")

                    visitor = FunctionCallVisitor()
                    visitor.visit(child)

                    if visitor.calls:
                        print("    CALLS:")

                        for call in visitor.calls:
                            print(f"      → {call}")

        elif isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            print(f"\nFUNCTION: {node.name}")

            visitor = FunctionCallVisitor()
            visitor.visit(node)

            if visitor.calls:
                print("  CALLS:")

                for call in visitor.calls:
                    print(f"    → {call}")


if __name__ == "__main__":
    analyze_file()