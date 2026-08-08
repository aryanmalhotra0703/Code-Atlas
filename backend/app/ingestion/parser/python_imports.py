import ast


def extract_imports(source_code: str) -> list[str]:
    """
    Parses a Python file's source and returns every module it imports,
    using Python's own parser (the `ast` module) rather than pattern-
    matching text. This correctly handles multi-line imports, aliases,
    relative imports, and imports nested inside functions or conditionals
    -- all things a regex-based approach would get wrong or miss silently.

    Returns dotted module names, e.g. "os.path", "httpie.client".
    Relative imports (from . import utils) keep their leading dots
    (".utils") -- resolving those to real file paths is a separate,
    later step, not something the parser itself needs to know about.
    """
    tree = ast.parse(source_code)
    imports = []

    for node in ast.walk(tree):
        # Handles: import os / import os.path / import os as o
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        # Handles: from os import path / from . import utils / from ..pkg import x
        elif isinstance(node, ast.ImportFrom):
            dots = "." * (node.level or 0)  # node.level counts leading dots
            module = node.module or ""
            imports.append(f"{dots}{module}")

    return imports