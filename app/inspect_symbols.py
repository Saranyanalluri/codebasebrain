import json
from pathlib import Path


SYMBOLS_PATH = Path(
    "data/indexes/symbols.json"
)


def inspect_symbols():
    with SYMBOLS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        symbols = json.load(file)

    print(f"Total symbols: {len(symbols)}")

    print("\nFirst 10 symbols:\n")

    for symbol in symbols[:10]:
        print(
            f"{symbol['qualified_name']} "
            f"| {symbol['type']} "
            f"| {symbol['file']} "
            f"| line {symbol['line']}"
        )


if __name__ == "__main__":
    inspect_symbols()