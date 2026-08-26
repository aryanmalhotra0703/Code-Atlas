from app.ingestion.parser.import_resolver import resolve_import


def test_resolves_absolute_dotted_import_to_real_file():
    all_paths = {"httpie/core.py", "httpie/client.py"}
    result = resolve_import("httpie.client", "httpie/core.py", all_paths)
    assert result == "httpie/client.py"


def test_resolves_absolute_dotted_import_to_package_init():
    all_paths = {"httpie/cli/__init__.py", "httpie/core.py"}
    result = resolve_import("httpie.cli", "httpie/core.py", all_paths)
    assert result == "httpie/cli/__init__.py"


def test_resolves_relative_import_within_same_package():
    all_paths = {"httpie/cli/argparser.py", "httpie/cli/constants.py"}
    result = resolve_import(".constants", "httpie/cli/argparser.py", all_paths)
    assert result == "httpie/cli/constants.py"


def test_resolves_bare_same_directory_import():
    all_paths = {"docs/contributors/fetch.py", "docs/contributors/generate.py"}
    result = resolve_import("fetch", "docs/contributors/generate.py", all_paths)
    assert result == "docs/contributors/fetch.py"


def test_external_import_returns_none():
    all_paths = {"httpie/core.py"}
    result = resolve_import("requests", "httpie/core.py", all_paths)
    assert result is None


def test_stdlib_import_returns_none():
    all_paths = {"httpie/core.py"}
    result = resolve_import("os.path", "httpie/core.py", all_paths)
    assert result is None