import ast
from pathlib import Path


REPOSITORY_PATH = Path(
    "data/repositories/flask/src/flask"
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

        call_name = self.get_call_name(node.func)

        if call_name:

            self.calls.append({
                "caller": (
                    self.current_function
                    if self.current_function
                    else "<module>"
                ),
                "callee": call_name,
                "line": node.lineno,
            })

        self.generic_visit(node)

    def get_call_name(self, node):

        # foo()
        if isinstance(node, ast.Name):
            return node.id

        # self.foo()
        # obj.foo()
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


def analyze_file(file_path):

    source_code = file_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source_code)

    visitor = CallVisitor()

    visitor.visit(tree)

    return visitor.calls


def main():

    file_path = (
        REPOSITORY_PATH / "app.py"
    )

    calls = analyze_file(file_path)

    print(
        f"Calls found in {file_path.name}: "
        f"{len(calls)}"
    )

    print("\nFirst 50 calls:\n")

    for call in calls[:50]:

        print(
            f"{call['caller']} "
            f"→ CALLS → "
            f"{call['callee']} "
            f"(line {call['line']})"
        )


if __name__ == "__main__":
    main()