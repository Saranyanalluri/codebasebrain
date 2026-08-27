from pathlib import Path
from collections import Counter

REPOSITORY_PATH = Path("data/repositories/flask")

IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    ".venv",
}


def get_files():
    files = []

    for file in REPOSITORY_PATH.rglob("*"):
        if not file.is_file():
            continue

        if any(part in IGNORED_DIRECTORIES for part in file.parts):
            continue

        files.append(file)

    return files


def inspect_repository():
    files = get_files()

    print(f"Total files: {len(files)}")

    directories = Counter()

    for file in files:
        relative_path = file.relative_to(REPOSITORY_PATH)

        if len(relative_path.parts) > 1:
            top_level_directory = relative_path.parts[0]
        else:
            top_level_directory = "[root]"

        directories[top_level_directory] += 1

    print("\nFiles by top-level directory:")

    for directory, count in directories.most_common():
        print(f"{directory}: {count}")


if __name__ == "__main__":
    inspect_repository()