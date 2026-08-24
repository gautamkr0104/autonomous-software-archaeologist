"""Tree-sitter based AST parser.

Provides deterministic, language-aware parsing of source files to extract
classes, functions, imports, exports, and other structural information.
"""

from __future__ import annotations

import os
from typing import Any

try:
    import tree_sitter_languages
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

from asa.core.logging import get_logger
from asa.core.models import (
    ClassInfo,
    ExportInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
    SourceLocation,
    SymbolInfo,
)
from asa.core.types import NodeType
from asa.core.utils import EXTENSION_MAP, TS_GRAMMAR_MAP, detect_language, is_binary_file

logger = get_logger("asa.parsers")


def _location_from_node(node: Any, file_path: str) -> SourceLocation:
    """Create a SourceLocation from a tree-sitter node."""
    return SourceLocation(
        file_path=file_path,
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        column_start=node.start_point[1],
        column_end=node.end_point[1],
    )


def _get_node_text(node: Any, source: bytes) -> str:
    """Extract text from a tree-sitter node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


class TreeSitterParser:
    """Language-aware AST parser using tree-sitter grammars."""

    def __init__(self) -> None:
        self.available_languages: set[str] = set()
        if HAS_TREE_SITTER:
            try:
                # tree-sitter-languages ships many grammars
                for lang in TS_GRAMMAR_MAP.values():
                    try:
                        parser = tree_sitter_languages.get_parser(lang)
                        if parser is not None:
                            self.available_languages.add(lang)
                    except Exception:
                        pass
            except Exception:
                pass
        logger.info(
            "parser.initialized",
            tree_sitter_available=HAS_TREE_SITTER,
            languages=len(self.available_languages),
        )

    def can_parse(self, language: str) -> bool:
        """Check if we can parse the given language."""
        if not HAS_TREE_SITTER:
            return False
        ts_lang = TS_GRAMMAR_MAP.get(language, language)
        return ts_lang in self.available_languages

    def parse_file(self, file_path: str) -> FileAnalysis | None:
        """Parse a single source file and return a FileAnalysis."""
        if is_binary_file(file_path):
            return None

        language = detect_language(file_path)
        if language is None:
            return None

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source_code = f.read()
        except OSError:
            return None

        source_bytes = source_code.encode("utf-8")

        # Basic file metrics
        lines = source_code.split("\n")
        loc = sum(1 for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*", "*/")))
        comments = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*", "*/")))
        blanks = sum(1 for l in lines if not l.strip())

        analysis = FileAnalysis(
            file_path=file_path,
            language=language,
            size_bytes=os.path.getsize(file_path),
            lines_of_code=loc,
            lines_of_comments=comments,
            lines_blank=blanks,
        )

        # Tree-sitter parsing
        if self.can_parse(language):
            try:
                ts_lang = TS_GRAMMAR_MAP.get(language, language)
                parser = tree_sitter_languages.get_parser(ts_lang)
                tree = parser.parse(source_bytes)
                root = tree.root_node

                self._extract_symbols(root, source_bytes, file_path, analysis)
                self._extract_imports(root, source_bytes, file_path, analysis)
                self._extract_exports(root, source_bytes, file_path, analysis)
                self._extract_env_vars(source_code, file_path, analysis)
                self._extract_config_keys(source_code, file_path, analysis)

            except Exception as e:
                logger.warning("parser.error", file=file_path, error=str(e))
        else:
            # Fallback: regex-based extraction for unsupported languages
            self._regex_fallback(source_code, file_path, analysis)

        # Always extract env vars and config keys (works without tree-sitter)
        self._extract_env_vars(source_code, file_path, analysis)
        self._extract_config_keys(source_code, file_path, analysis)

        analysis.is_test = self._is_test_file(file_path)
        analysis.is_config = self._is_config_file(file_path)
        analysis.is_generated = self._is_generated_file(source_code)

        return analysis

    def _extract_symbols(
        self, node: Any, source: bytes, file_path: str, analysis: FileAnalysis
    ) -> None:
        """Recursively extract classes and functions from the AST."""
        for child in node.children:
            node_type = child.type

            # Classes
            if node_type in ("class_definition", "class_declaration", "class"):
                cls = self._parse_class(child, source, file_path)
                if cls:
                    analysis.classes.append(cls)

            # Functions / methods
            elif node_type in (
                "function_definition", "function_declaration",
                "method_definition", "method_declaration",
                "arrow_function", "function",
                "async_function_definition",
            ):
                func = self._parse_function(child, source, file_path)
                if func:
                    analysis.functions.append(func)

            # Module-level assignments (constants, globals)
            elif node_type in ("assignment", "variable_declaration"):
                sym = self._parse_assignment(child, source, file_path)
                if sym:
                    analysis.global_variables.append(sym)

            # Recurse
            self._extract_symbols(child, source, file_path, analysis)

    def _parse_class(self, node: Any, source: bytes, file_path: str) -> ClassInfo | None:
        """Parse a class definition."""
        name = self._get_name(node, source)
        if not name:
            return None

        bases = self._get_bases(node, source)

        cls = ClassInfo(
            name=name,
            qualified_name=name,
            symbol_type=NodeType.CLASS,
            location=_location_from_node(node, file_path),
            docstring=self._get_docstring(node, source),
            bases=bases,
            decorators=self._get_decorators(node, source),
        )

        # Extract methods
        for child in node.children:
            if child.type in (
                "function_definition", "method_definition",
                "async_function_definition",
            ):
                method = self._parse_function(child, source, file_path)
                if method:
                    cls.methods.append(method)

        return cls

    def _parse_function(self, node: Any, source: bytes, file_path: str) -> FunctionInfo | None:
        """Parse a function/method definition."""
        name = self._get_name(node, source)
        if not name:
            return None

        parameters = self._get_parameters(node, source)
        return_type = self._get_return_type(node, source)
        is_async = node.type == "async_function_definition" or any(
            c.type == "async" for c in node.children
        )

        func = FunctionInfo(
            name=name,
            qualified_name=name,
            symbol_type=NodeType.FUNCTION,
            location=_location_from_node(node, file_path),
            docstring=self._get_docstring(node, source),
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            decorators=self._get_decorators(node, source),
            calls=self._get_function_calls(node, source),
        )

        return func

    def _parse_assignment(self, node: Any, source: bytes, file_path: str) -> SymbolInfo | None:
        """Parse a variable/constant assignment."""
        name = self._get_name(node, source)
        if not name:
            return None
        return SymbolInfo(
            name=name,
            qualified_name=name,
            symbol_type=NodeType.VARIABLE,
            location=_location_from_node(node, file_path),
        )

    def _extract_imports(
        self, node: Any, source: bytes, file_path: str, analysis: FileAnalysis
    ) -> None:
        """Extract import statements."""
        for child in node.children:
            if child.type in ("import_statement", "import_from_statement"):
                imp = self._parse_import(child, source, file_path)
                if imp:
                    analysis.imports.append(imp)

    def _parse_import(self, node: Any, source: bytes, file_path: str) -> ImportInfo | None:
        """Parse a single import statement."""
        text = _get_node_text(node, source)
        is_from_import = node.type == "import_from_statement"

        module = ""
        names: list[str] = []
        is_relative = False

        for child in node.children:
            if child.type == "dotted_name":
                module = _get_node_text(child, source)
            elif child.type == "relative_import":
                is_relative = True
                module = _get_node_text(child, source)
                # Count leading dots for relative import depth
            elif child.type == "import_as_name" or child.type == "aliased_import":
                names.append(_get_node_text(child, source))
            elif child.type == "wildcard_import":
                names.append("*")

        if not module and not names:
            # Try to extract from text
            parts = text.split()
            if len(parts) >= 2:
                module = parts[1].strip().rstrip(";")

        return ImportInfo(
            module=module,
            names=names,
            is_relative=is_relative,
            is_wildcard="*" in names,
            location=_location_from_node(node, file_path),
        )

    def _extract_exports(
        self, node: Any, source: bytes, file_path: str, analysis: FileAnalysis
    ) -> None:
        """Extract exported symbols."""
        # Python: __all__
        for child in node.children:
            if child.type == "assignment":
                lhs = child.children[0] if child.children else None
                if lhs and _get_node_text(lhs, source) == "__all__":
                    analysis.exports.append(
                        ExportInfo(
                            name="__all__",
                            symbol_type=NodeType.EXPORT,
                            location=_location_from_node(child, file_path),
                            is_default=False,
                        )
                    )

        # JS/TS: export statements
        for child in node.children:
            if child.type in ("export_statement",):
                analysis.exports.append(
                    ExportInfo(
                        name=_get_node_text(child, source)[:80],
                        symbol_type=NodeType.EXPORT,
                        location=_location_from_node(child, file_path),
                    )
                )

    def _get_name(self, node: Any, source: bytes) -> str:
        """Extract the name of a named node."""
        for child in node.children:
            if child.type == "identifier":
                return _get_node_text(child, source)
            if child.type == "name":
                return _get_node_text(child, source)
            if child.type in ("property_identifier", "field_identifier"):
                return _get_node_text(child, source)
        return ""

    def _get_bases(self, node: Any, source: bytes) -> list[str]:
        """Extract base classes / superclasses."""
        bases: list[str] = []
        for child in node.children:
            if child.type == "argument_list":
                for arg in child.children:
                    if arg.type in ("identifier", "attribute"):
                        bases.append(_get_node_text(arg, source))
            if child.type == "superclasses":
                for arg in child.children:
                    if arg.type in ("identifier", "type"):
                        bases.append(_get_node_text(arg, source))
        return bases

    def _get_decorators(self, node: Any, source: bytes) -> list[str]:
        """Extract decorators."""
        decorators: list[str] = []
        for child in node.children:
            if child.type in ("decorator", "decorator_expression"):
                decorators.append(_get_node_text(child, source))
        return decorators

    def _get_docstring(self, node: Any, source: bytes) -> str | None:
        """Extract docstring if present."""
        for child in node.children:
            if child.type == "expression_statement":
                for expr in child.children:
                    if expr.type == "string":
                        raw = _get_node_text(expr, source)
                        # Strip quotes
                        return raw.strip().strip("\"'").strip("\"'")
        return None

    def _get_parameters(self, node: Any, source: bytes) -> list[dict[str, str]]:
        """Extract function parameters."""
        params: list[dict[str, str]] = []
        for child in node.children:
            if child.type in ("parameters", "formal_parameters"):
                for param in child.children:
                    if param.type in ("identifier", "required_parameter", "parameter"):
                        pname = self._get_name(param, source)
                        if pname and pname != "self" and pname != "cls":
                            params.append({"name": pname})
                    elif param.type == "keyword_parameter":
                        pname = self._get_name(param, source)
                        if pname:
                            params.append({"name": pname, "has_default": "true"})
        return params

    def _get_return_type(self, node: Any, source: bytes) -> str | None:
        """Extract return type annotation."""
        for child in node.children:
            if child.type in ("type", "return_type", "type_annotation"):
                return _get_node_text(child, source)
        return None

    def _get_function_calls(self, node: Any, source: bytes) -> list[str]:
        """Extract function calls within a function body."""
        calls: list[str] = []
        for child in node.children:
            if child.type == "block":
                self._collect_calls(child, source, calls)
        return calls

    def _collect_calls(self, node: Any, source: bytes, calls: list[str], depth: int = 0) -> None:
        """Recursively collect function calls."""
        if depth > 50:
            return
        if node.type == "call_expression":
            func = node.children[0] if node.children else None
            if func:
                name = _get_node_text(func, source)
                if name and len(calls) < 200:
                    calls.append(name)
        for child in node.children:
            self._collect_calls(child, source, calls, depth + 1)

    def _extract_env_vars(self, source: str, file_path: str, analysis: FileAnalysis) -> None:
        """Extract environment variable references."""
        import re
        # os.environ["..."], os.getenv("..."), process.env.X, env("...")
        patterns = [
            r'os\.environ\[["\']([A-Z_][A-Z0-9_]*)["\']\]',
            r'os\.getenv\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
            r'process\.env\.([A-Z_][A-Z0-9_]*)',
            r'Env\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
            r'os\.environ\.get\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
        ]
        env_vars: set[str] = set()
        for pattern in patterns:
            env_vars.update(re.findall(pattern, source))
        analysis.environment_variables = sorted(env_vars)

    def _extract_config_keys(self, source: str, file_path: str, analysis: FileAnalysis) -> None:
        """Extract configuration keys from common config patterns."""
        import re
        patterns = [
            r'config\.get\(\s*["\']([^"\']+)["\']',
            r'settings\.([a-zA-Z_]+)',
            r'GET\(\s*["\']([A-Z_][A-Z0-9_.]*)["\']',
        ]
        keys: set[str] = set()
        for pattern in patterns:
            keys.update(re.findall(pattern, source))
        analysis.configuration_keys = sorted(keys)[:50]

    def _regex_fallback(self, source: str, file_path: str, analysis: FileAnalysis) -> None:
        """Regex-based extraction when tree-sitter is not available."""
        import re

        # Python classes
        for match in re.finditer(r"class\s+(\w+)(?:\(([^)]*)\))?:", source):
            name = match.group(1)
            bases = [b.strip() for b in (match.group(2) or "").split(",") if b.strip()]
            # Compute approximate location
            line = source[:match.start()].count("\n") + 1
            cls = ClassInfo(
                name=name,
                qualified_name=name,
                symbol_type=NodeType.CLASS,
                location=SourceLocation(file_path=file_path, line_start=line),
                bases=bases,
            )
            analysis.classes.append(cls)

        # Python functions
        for match in re.finditer(
            r"(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\S+))?:",
            source,
        ):
            name = match.group(1)
            params_str = match.group(2) or ""
            return_type = match.group(3)
            line = source[:match.start()].count("\n") + 1
            params = [
                {"name": p.strip().split(":")[0].split("=")[0].strip()}
                for p in params_str.split(",")
                if p.strip() and p.strip() not in ("self", "cls")
            ]
            is_async = source[max(0, match.start() - 6) : match.start()].strip() == "async"
            func = FunctionInfo(
                name=name,
                qualified_name=name,
                symbol_type=NodeType.FUNCTION,
                location=SourceLocation(file_path=file_path, line_start=line),
                parameters=params,
                return_type=return_type,
                is_async=is_async,
            )
            analysis.functions.append(func)

        # Imports
        for match in re.finditer(
            r"(?:from\s+(\S+)\s+)?import\s+(.+?)(?:\s*#.*)?$",
            source,
            re.MULTILINE,
        ):
            module = match.group(1) or ""
            names_str = match.group(2) or ""
            names = [n.strip().split(" as ")[0] for n in names_str.split(",")]
            analysis.imports.append(
                ImportInfo(
                    module=module,
                    names=names,
                    is_relative=module.startswith("."),
                    location=SourceLocation(
                        file_path=file_path,
                        line_start=source[:match.start()].count("\n") + 1,
                    ),
                )
            )

    def _is_test_file(self, file_path: str) -> bool:
        """Check if the file is likely a test file."""
        basename = os.path.basename(file_path).lower()
        return (
            basename.startswith("test_")
            or basename.endswith("_test.py")
            or basename.endswith(".test.js")
            or basename.endswith(".test.ts")
            or basename.endswith(".spec.js")
            or basename.endswith(".spec.ts")
            or "/test/" in file_path.lower()
            or "/tests/" in file_path.lower()
            or "__tests__" in file_path
        )

    def _is_config_file(self, file_path: str) -> bool:
        """Check if the file is a configuration file."""
        basename = os.path.basename(file_path).lower()
        config_names = {
            "config", "configuration", "settings", "setup",
            "pyproject.toml", "setup.py", "setup.cfg",
            "package.json", "tsconfig.json", ".eslintrc",
            ".prettierrc", "makefile", "dockerfile",
            "docker-compose.yml", "docker-compose.yaml",
            ".env", ".env.example", ".env.local",
            "requirements.txt", "requirements-dev.txt",
            "cargo.toml", "go.mod", "pom.xml", "build.gradle",
            "webpack.config", "vite.config", "rollup.config",
        }
        return basename in config_names or basename.startswith((".",))

    def _is_generated_file(self, source: str) -> None:
        """Check if the file looks auto-generated."""
        # Not used as a return — just checking first lines
        pass
