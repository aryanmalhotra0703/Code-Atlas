import posixpath

from app.ingestion.parser.python_imports import extract_imports


def resolve_import(module: str, current_path: str, all_paths: set[str]) -> str | None:
    """
    Attempts to map a raw import string (from extract_imports) to an
    actual file path within the same repo. Returns None if the import is
    external (a third-party package or the standard library) -- which is
    the expected, common case: most imports in any file are external,
    only a handful are ever local to the repo itself.

    This is a heuristic, not a perfect resolver -- Python's real import
    system also considers sys.path, installed packages, and namespace
    packages, none of which we have visibility into here. What follows
    covers the common, real-world cases without trying to fully
    reimplement Python's import machinery.
    """
    current_dir = posixpath.dirname(current_path)

    if module.startswith("."):
        level = len(module) - len(module.lstrip("."))
        remainder = module[level:]
        base_dir = current_dir
        for _ in range(level - 1):
            base_dir = posixpath.dirname(base_dir)
        candidate_base = posixpath.join(base_dir, remainder.replace(".", "/")) if remainder else base_dir
    else:
        candidate_base = module.replace(".", "/")

    for candidate in (f"{candidate_base}.py", posixpath.join(candidate_base, "__init__.py")):
        if candidate in all_paths:
            return candidate

    if "." not in module and not module.startswith("."):
        sibling = posixpath.join(current_dir, f"{module}.py")
        if sibling in all_paths:
            return sibling

    return None


def build_import_edges(files: dict[str, str]) -> list[tuple[str, str]]:
    """
    Runs the parser across every file and resolves each import to a real
    file path where possible. Returns (from_file, to_file) pairs -- these
    are exactly the IMPORTS edges that will get loaded into Neo4j next.
    External imports (the majority) are silently dropped, since an edge
    to something outside the repo isn't part of this repo's graph.
    """
    all_paths = set(files.keys())
    edges: list[tuple[str, str]] = []

    for path, source in files.items():
        try:
            imports = extract_imports(source)
        except SyntaxError:
            continue

        for module in imports:
            resolved = resolve_import(module, path, all_paths)
            if resolved and resolved != path:
                edges.append((path, resolved))

    return edges