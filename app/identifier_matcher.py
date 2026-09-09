import re


IDENTIFIER_PATTERN = re.compile(
    r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\b"
)


def extract_identifiers(text):
    """
    Extract code-like identifiers from text.

    Examples:
        add_url_rule
        save_session
        Flask.add_url_rule
        SecureCookieSessionInterface.save_session
    """

    candidates = IDENTIFIER_PATTERN.findall(
        text
    )

    identifiers = []

    for candidate in candidates:

        # Ignore ordinary natural-language words.
        if (
            "_" in candidate
            or "." in candidate
        ):
            identifiers.append(
                candidate
            )

    return list(
        dict.fromkeys(
            identifiers
        )
    )


def identifier_match_score(
    query,
    qualified_name
):
    """
    Calculate an exact identifier-match score.

    Returns:
        1.0 -> exact identifier match
        0.5 -> partial identifier match
        0.0 -> no identifier match
    """

    query_identifiers = extract_identifiers(
        query
    )

    if not query_identifiers:
        return 0.0

    normalized_name = (
        qualified_name.lower()
    )

    normalized_parts = (
        normalized_name.split(".")
    )

    score = 0.0

    for identifier in query_identifiers:

        identifier = identifier.lower()

        if identifier == normalized_name:
            score = max(
                score,
                1.0
            )

        elif identifier in normalized_parts:
            score = max(
                score,
                1.0
            )

        elif identifier in normalized_name:
            score = max(
                score,
                0.5
            )

    return score


if __name__ == "__main__":

    queries = [
        "How does Flask register URL rules?",
        "add_url_rule",
        "Flask.add_url_rule",
        "How are sessions saved?",
        "SecureCookieSessionInterface.save_session",
    ]

    names = [
        "App.add_url_rule",
        "Scaffold.add_url_rule",
        "SecureCookieSessionInterface.save_session",
        "Flask.url_for",
    ]

    for query in queries:

        print(
            f"\nQuery: {query}"
        )

        print(
            "Identifiers:",
            extract_identifiers(query)
        )

        for name in names:

            score = identifier_match_score(
                query,
                name
            )

            if score > 0:

                print(
                    f"  {name}: "
                    f"{score:.1f}"
                )