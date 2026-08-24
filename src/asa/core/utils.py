"""Shared utility functions."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".clj": "clojure",
    ".vue": "vue",
    ".svelte": "svelte",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}

# Tree-sitter grammar names — may differ from our internal names
TS_GRAMMAR_MAP: dict[str, str] = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "c": "c",
    "cpp": "cpp",
    "csharp": "c_sharp",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "scala": "scala",
    "sql": "sql",
    "bash": "bash",
    "shell": "bash",
    "r": "r",
    "lua": "lua",
    "html": "html",
    "css": "css",
    "json": "json",
    "yaml": "yaml",
    "toml": "toml",
}

SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", "node_modules", "dist", "build",
    ".next", ".nuxt", "vendor", "venv", ".venv", "env", ".env",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", "out", "bin", "obj", ".gradle", ".idea", ".vscode",
    "coverage", ".coverage", "htmlcov", ".eggs", "*.egg-info",
})

BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".o", ".obj",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo", ".class", ".jar",
    ".sqlite", ".db", ".sqlite3",
})


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file extension."""
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext)


def is_binary_file(file_path: str) -> bool:
    """Quick check if a file is likely binary."""
    ext = Path(file_path).suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
    except (OSError, PermissionError):
        return True
    return False


def should_skip_dir(dir_name: str) -> bool:
    """Check if a directory should be skipped during traversal."""
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


def file_hash(file_path: str) -> str:
    """SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def relative_import_path(from_file: str, import_module: str, is_relative: bool) -> str:
    """Resolve an import to an approximate file path."""
    if not is_relative:
        return import_module.replace(".", "/")

    from_dir = os.path.dirname(from_file)
    dots = len(import_module) - len(import_module.lstrip("."))
    module_part = import_module[dots:]

    parent = from_dir
    for _ in range(dots - 1):
        parent = os.path.dirname(parent)

    if module_part:
        return os.path.join(parent, module_part.replace(".", "/"))
    return parent


def snake_to_camel(name: str) -> str:
    """Convert snake_case to CamelCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
