import re

from app.services.agents.base_agent import BaseAgent


CODING_GUIDES = {
    "list comprehension": (
        "A Python list comprehension builds a list from an iterable in one expression. "
        "Keep it concise; use a normal loop when logic becomes hard to read.\n\n"
        "```python\nsquares = [number ** 2 for number in range(5)]\n```"
    ),
    "async await": (
        "`async` defines a coroutine and `await` pauses that coroutine until another awaitable "
        "finishes without blocking the event loop. Use it for concurrent I/O, not CPU-heavy work.\n\n"
        "```python\nasync def load_data(client):\n    response = await client.get('/data')\n    return response.json()\n```"
    ),
    "recursion": (
        "Recursion solves a problem by calling the same function on a smaller input. Every recursive "
        "function needs a base case and must make progress toward it.\n\n"
        "```python\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n```"
    ),
    "loop": (
        "A loop repeats work. Use a `for` loop when iterating over known values and a `while` loop "
        "when repetition depends on a condition.\n\n"
        "```python\nfor item in items:\n    print(item)\n```"
    ),
    "rest graphql": (
        "REST models resources behind multiple HTTP endpoints; GraphQL exposes a typed query schema, "
        "usually through one endpoint. REST is simple and cache-friendly, while GraphQL lets clients "
        "select response fields but adds schema and resolver complexity."
    ),
    "exception": (
        "Handle only exceptions you can recover from, keep the protected block narrow, and preserve "
        "diagnostic context when re-raising.\n\n"
        "```python\ntry:\n    value = int(raw)\nexcept ValueError as exc:\n    raise ValueError('Expected an integer') from exc\n```"
    ),
    "javascript function": (
        "A JavaScript function packages reusable behavior. Arrow functions capture lexical `this`; "
        "regular functions receive `this` from how they are called.\n\n"
        "```javascript\nconst add = (left, right) => left + right;\n```"
    ),
    "python": (
        "For Python help, include the smallest reproducible code sample, the full traceback, and the "
        "behavior you expected. I can then match it to a known language concept or error pattern."
    ),
    "api": (
        "An API defines how software components communicate. A robust HTTP API validates inputs, uses "
        "meaningful status codes, authenticates callers, versions contracts, and returns consistent errors."
    ),
    "database": (
        "Database code should use parameterized queries, transactions for related writes, indexes based "
        "on measured access patterns, and migrations for repeatable schema changes."
    ),
}

ALIASES = {
    "async/await": "async await",
    "asyncio": "async await",
    "for loop": "loop",
    "while loop": "loop",
    "graphql": "rest graphql",
    "rest api": "rest graphql",
    "try except": "exception",
    "error": "exception",
    "js function": "javascript function",
    "sql": "database",
}


class CodingHelpAgent(BaseAgent):
    name = "coding_help"

    def handle(self, message: str, history: list[dict[str, str]]) -> str:
        del history
        normalized = re.sub(r"[^a-z0-9/ ]", " ", message.casefold())
        for alias, canonical in ALIASES.items():
            if alias in normalized:
                return CODING_GUIDES[canonical]
        for concept, explanation in CODING_GUIDES.items():
            if concept in normalized:
                return explanation
        return (
            "Can you tell me which programming language or concept you need help with? "
            "Include a short code sample and exact error when applicable."
        )
