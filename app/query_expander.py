import re


QUERY_EXPANSIONS = {
    "register url rules": [
        "add_url_rule",
        "url_map",
        "endpoint",
        "view_func",
        "route",
    ],
    "routing": [
        "add_url_rule",
        "url_map",
        "endpoint",
        "route",
    ],
    "save sessions": [
        "save_session",
        "SessionInterface",
        "SecureCookieSessionInterface",
        "session",
        "cookie",
    ],
    "user sessions": [
        "save_session",
        "SessionInterface",
        "SecureCookieSessionInterface",
        "session",
    ],
    "handle exceptions": [
        "handle_exception",
        "handle_user_exception",
        "errorhandler",
        "HTTPException",
    ],
    "process request": [
        "full_dispatch_request",
        "dispatch_request",
        "preprocess_request",
        "process_response",
        "request",
    ],
    "send static file": [
        "send_static_file",
        "send_file",
        "send_from_directory",
        "static_folder",
    ],
}


def expand_query(query):

    normalized_query = re.sub(
        r"\s+",
        " ",
        query.lower().strip()
    )

    expanded_terms = []

    for phrase, terms in QUERY_EXPANSIONS.items():

        if phrase in normalized_query:

            expanded_terms.extend(
                terms
            )

    # Remove duplicate terms while
    # preserving their original order.
    expanded_terms = list(
        dict.fromkeys(
            expanded_terms
        )
    )

    if not expanded_terms:

        return query

    return (
        query
        + " "
        + " ".join(
            expanded_terms
        )
    )


if __name__ == "__main__":

    queries = [
        "How does Flask register URL rules?",
        "How are user sessions saved in Flask?",
        "How does Flask handle exceptions?",
        "How does Flask dispatch an incoming HTTP request?",
        "How does Flask send a static file?",
    ]

    for query in queries:

        print(
            f"\nOriginal: {query}"
        )

        print(
            f"Expanded: "
            f"{expand_query(query)}"
        )