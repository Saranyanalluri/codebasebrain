import ast
import json
from pathlib import Path


REPOSITORY_PATH = Path(
    "data/repositories/flask/src/flask"
)

OUTPUT_PATH = Path(
    "data/indexes/resolved_imports.json"
)


class ImportVisitor(ast.NodeVisitor):

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):

        for alias in node.names:

            self.imports.append({
                "module": alias.name,
                "name": None,
                "level": 0,
                "line": node.lineno,
            })

        self.generic_visit(node)

    def visit_ImportFrom(self, node):

        module = node.module or ""
        for alias in node.names:

            self.imports.append({
                    "module": module,
                    "name": alias.name,
                     "level": node.level,
                     "line": node.lineno,
            })
        self.generic_visit(node)


def analyze_file(file_path):

    source = file_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    visitor = ImportVisitor()

    visitor.visit(tree)

    return visitor.imports


def resolve_relative_import(
    current_file,
    module,
    name,
    level
):

    if level == 0:
        return None

    current_dir = current_file.parent

    for _ in range(level - 1):
        current_dir = current_dir.parent

    if module:
        target = current_dir.joinpath(
            *module.split(".")
        )

    else:
        target = current_dir / name

    py_file = target.with_suffix(".py")

    if py_file.exists():
        return py_file

    init_file = target / "__init__.py"

    if init_file.exists():
        return init_file

    return None


def analyze_repository():

    resolved = []

    python_files = list(
        REPOSITORY_PATH.rglob("*.py")
    )

    for file_path in python_files:

        imports = analyze_file(
            file_path
        )

        for item in imports:

            target = resolve_relative_import(
                file_path,
                item["module"],
                item["name"],
                item["level"]
            )

            if target is None:
                continue

            resolved.append({
                "source": str(
                    file_path.relative_to(
                        REPOSITORY_PATH
                    )
                ).replace("\\", "/"),

                "target": str(
                    target.relative_to(
                        REPOSITORY_PATH
                    )
                ).replace("\\", "/"),

                "type": "IMPORTS",

                "line": item["line"],
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

    print(
        "Resolving repository imports..."
    )

    imports = analyze_repository()

    print(
        f"Internal imports found: "
        f"{len(imports)}"
    )

    save_results(imports)

    print(
        f"Saved imports to: "
        f"{OUTPUT_PATH}"
    )

    print("\nFirst 30 imports:\n")

    for edge in imports[:30]:

        print(
            f"{edge['source']} "
            f"→ IMPORTS → "
            f"{edge['target']} "
            f"(line {edge['line']})"
        )


if __name__ == "__main__":
    main()