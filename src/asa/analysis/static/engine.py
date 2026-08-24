"""Static analysis engine.

Orchestrates the complete static analysis pipeline:
  1. Walk the repository
  2. Parse each file with tree-sitter
  3. Extract imports, classes, functions, etc.
  4. Build the dependency graph
  5. Detect package-level dependencies
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

from asa.analysis.extractors.dependency_graph_builder import DependencyGraphBuilder
from asa.analysis.parsers.tree_sitter_parser import TreeSitterParser
from asa.config.settings import Settings, get_settings
from asa.core.logging import get_logger
from asa.core.models import (
    DependencyGraph,
    FileAnalysis,
    FileDependency,
    ModuleInfo,
    ProjectAnalysis,
    RepositoryInfo,
)
from asa.core.types import AnalysisPhase
from asa.core.utils import detect_language, is_binary_file, should_skip_dir

logger = get_logger("asa.static")


class StaticAnalysisEngine:
    """Runs the complete static analysis pipeline on an ingested repository."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.parser = TreeSitterParser()
        self.graph_builder = DependencyGraphBuilder()

    def analyze(self, repo_info: RepositoryInfo) -> ProjectAnalysis:
        """Run full static analysis on the repository."""
        start_time = time.time()

        logger.info("static.start", repo=repo_info.name, path=repo_info.local_path)

        project = ProjectAnalysis(repository=repo_info)

        # Phase 1: Discover and parse all files
        logger.info("static.parsing_files")
        project.file_analyses = self._parse_all_files(repo_info.local_path)
        logger.info("static.files_parsed", count=len(project.file_analyses))

        # Phase 2: Discover modules/packages
        logger.info("static.discovering_modules")
        project.modules = self._discover_modules(repo_info.local_path, project.file_analyses)
        logger.info("static.modules_found", count=len(project.modules))

        # Phase 3: Discover package-level dependencies
        logger.info("static.discovering_dependencies")
        project.external_dependencies = self._discover_package_deps(repo_info.local_path)
        logger.info("static.external_deps", count=len(project.external_dependencies))

        # Phase 4: Build dependency graph
        logger.info("static.building_graph")
        project.dependency_graph = self.graph_builder.build(project)
        logger.info("static.graph_built",
                     nodes=len(project.dependency_graph.nodes),
                     edges=len(project.dependency_graph.edges))

        # Record phase result
        elapsed = time.time() - start_time
        from asa.core.models import AnalysisResult
        project.phase_results.append(AnalysisResult(
            phase=AnalysisPhase.STATIC_ANALYSIS,
            status="completed",
            started_at=datetime.utcfromtimestamp(start_time),
            completed_at=datetime.utcnow(),
            duration_seconds=round(elapsed, 2),
            files_analyzed=len(project.file_analyses),
            symbols_extracted=project.total_symbols,
            relationships_found=project.total_relationships,
        ))

        logger.info(
            "static.complete",
            elapsed=f"{elapsed:.1f}s",
            files=len(project.file_analyses),
            symbols=project.total_symbols,
            relationships=project.total_relationships,
        )

        return project

    def _parse_all_files(self, repo_path: str) -> list[FileAnalysis]:
        """Walk the repository and parse every analyzable file."""
        analyses: list[FileAnalysis] = []
        count = 0

        for root, dirs, files in os.walk(repo_path):
            # Filter out skipped directories
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]

            for filename in sorted(files):
                if count >= self.settings.max_files_analyzed:
                    logger.warning("static.file_limit_reached", limit=self.settings.max_files_analyzed)
                    return analyses

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)

                # Skip binary files
                if is_binary_file(file_path):
                    continue

                # Skip very large files
                try:
                    size = os.path.getsize(file_path)
                    if size > self.settings.max_file_size_mb * 1024 * 1024:
                        continue
                except OSError:
                    continue

                # Check if we can analyze this language
                language = detect_language(rel_path)
                if language is None:
                    continue

                # Parse the file
                try:
                    analysis = self.parser.parse_file(file_path)
                    if analysis:
                        # Normalize path to use forward slashes and repo-relative
                        analysis.file_path = rel_path.replace("\\", "/")
                        analyses.append(analysis)
                        count += 1
                except Exception as e:
                    logger.debug("static.parse_error", file=rel_path, error=str(e))

        return analyses

    def _discover_modules(
        self, repo_path: str, file_analyses: list[FileAnalysis]
    ) -> list[ModuleInfo]:
        """Discover logical modules/packages."""
        modules: dict[str, ModuleInfo] = {}

        # Detect packages by __init__.py
        for fa in file_analyses:
            if os.path.basename(fa.file_path) == "__init__.py":
                dir_path = os.path.dirname(fa.file_path)
                mod_name = dir_path.replace("/", ".").replace("\\", ".")
                if mod_name not in modules:
                    modules[mod_name] = ModuleInfo(
                        name=mod_name,
                        path=dir_path,
                        language=fa.language,
                    )
                modules[mod_name].files.append(fa.file_path)

        # Group files into modules by directory
        dir_files: dict[str, list[FileAnalysis]] = {}
        for fa in file_analyses:
            dir_path = os.path.dirname(fa.file_path)
            if dir_path not in dir_files:
                dir_files[dir_path] = []
            dir_files[dir_path].append(fa)

        for dir_path, files in dir_files.items():
            # Create module for directories with multiple files
            if len(files) >= 2 and dir_path not in modules:
                mod_name = dir_path.replace("/", ".").replace("\\", ".")
                modules[mod_name] = ModuleInfo(
                    name=mod_name,
                    path=dir_path,
                    files=[f.file_path for f in files],
                    language=files[0].language if files else "",
                )
            elif dir_path in modules:
                for f in files:
                    if f.file_path not in modules[dir_path].files:
                        modules[dir_path].files.append(f.file_path)

        # Determine submodules
        mod_list = list(modules.values())
        for mod in mod_list:
            for other in mod_list:
                if other != mod and other.path.startswith(mod.path + "/"):
                    if other.name not in mod.submodules:
                        mod.submodules.append(other.name)

        # Extract public API (exported symbols)
        for fa in file_analyses:
            for exp in fa.exports:
                # Find which module this file belongs to
                dir_path = os.path.dirname(fa.file_path)
                if dir_path in modules:
                    modules[dir_path].public_api.append(exp.name)

        return sorted(mod_list, key=lambda m: m.name)

    def _discover_package_deps(self, repo_path: str) -> list[FileDependency]:
        """Discover package-level dependencies from manifest files."""
        deps: list[FileDependency] = []
        seen: set[str] = set()

        dep_files = [
            ("requirements.txt", self._parse_requirements),
            ("setup.py", self._parse_setup_py),
            ("pyproject.toml", self._parse_pyproject_toml),
            ("package.json", self._parse_package_json),
            ("go.mod", self._parse_go_mod),
            ("Cargo.toml", self._parse_cargo_toml),
            ("pom.xml", self._parse_pom_xml),
            ("Gemfile", self._parse_gemfile),
            ("composer.json", self._parse_composer_json),
        ]

        for filename, parser_fn in dep_files:
            file_path = os.path.join(repo_path, filename)
            if os.path.exists(file_path):
                try:
                    new_deps = parser_fn(file_path)
                    for d in new_deps:
                        if d.name not in seen:
                            seen.add(d.name)
                            deps.append(d)
                except Exception as e:
                    logger.debug("static.dep_parse_error", file=filename, error=str(e))

        # Also check nested requirements files
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]
            for f in files:
                if f == "requirements.txt" and os.path.join(root, f) != os.path.join(repo_path, "requirements.txt"):
                    try:
                        new_deps = self._parse_requirements(os.path.join(root, f))
                        for d in new_deps:
                            if d.name not in seen:
                                seen.add(d.name)
                                d.is_development = "dev" in root.lower()
                                deps.append(d)
                    except Exception:
                        pass

        return deps

    def _parse_requirements(self, path: str) -> list[FileDependency]:
        """Parse requirements.txt."""
        deps = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Handle package==version or package>=version
                parts = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
                name = parts.strip().split("[")[0]  # Remove extras
                deps.append(FileDependency(
                    name=name,
                    version=line.replace(parts, "").strip() or None,
                    source_file=os.path.basename(path),
                ))
        return deps

    def _parse_setup_py(self, path: str) -> list[FileDependency]:
        """Basic parsing of setup.py."""
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            # Look for install_requires
            import re
            match = re.search(r"install_requires\s*=\s*\[([^\]]+)\]", content)
            if match:
                for dep_str in match.group(1).split(","):
                    dep_str = dep_str.strip().strip("'\"")
                    if dep_str:
                        name = dep_str.split("==")[0].split(">=")[0].strip()
                        deps.append(FileDependency(name=name, source_file="setup.py"))
        except OSError:
            pass
        return deps

    def _parse_pyproject_toml(self, path: str) -> list[FileDependency]:
        """Basic parsing of pyproject.toml."""
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            import re
            # Find dependencies = [...] under [project]
            match = re.search(r"dependencies\s*=\s*\[([^\]]+)\]", content)
            if match:
                for dep_str in match.group(1).split(","):
                    dep_str = dep_str.strip().strip("'\"")
                    if dep_str:
                        name = dep_str.split("==")[0].split(">=")[0].split("<")[0].strip()
                        deps.append(FileDependency(name=name, source_file="pyproject.toml"))
        except OSError:
            pass
        return deps

    def _parse_package_json(self, path: str) -> list[FileDependency]:
        """Parse package.json dependencies."""
        import json
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            for section in ["dependencies", "devDependencies"]:
                dep_dict = data.get(section, {})
                is_dev = section == "devDependencies"
                for name, version in dep_dict.items():
                    deps.append(FileDependency(
                        name=name,
                        version=version,
                        is_development=is_dev,
                        source_file="package.json",
                    ))
        except (json.JSONDecodeError, OSError):
            pass
        return deps

    def _parse_go_mod(self, path: str) -> list[FileDependency]:
        """Parse go.mod."""
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                in_require = False
                for line in f:
                    line = line.strip()
                    if line.startswith("require ("):
                        in_require = True
                        continue
                    if line == ")" and in_require:
                        in_require = False
                        continue
                    if in_require and line:
                        parts = line.split()
                        if len(parts) >= 2:
                            deps.append(FileDependency(
                                name=parts[0],
                                version=parts[1],
                                source_file="go.mod",
                            ))
                    elif line.startswith("require ") and "(" not in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            deps.append(FileDependency(
                                name=parts[1],
                                version=parts[2],
                                source_file="go.mod",
                            ))
        except OSError:
            pass
        return deps

    def _parse_cargo_toml(self, path: str) -> list[FileDependency]:
        """Parse Cargo.toml."""
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            import re
            match = re.search(r"\[dependencies\](.*?)(?:\[|$)", content, re.DOTALL)
            if match:
                for line in match.group(1).split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=")
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            version = parts[1].strip().strip("'\"")
                            deps.append(FileDependency(
                                name=name, version=version, source_file="Cargo.toml",
                            ))
        except OSError:
            pass
        return deps

    def _parse_pom_xml(self, path: str) -> list[FileDependency]:
        """Basic pom.xml parsing."""
        deps = []
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            for dep in root.findall(".//m:dependency", ns):
                group_id = dep.find("m:groupId", ns)
                artifact_id = dep.find("m:artifactId", ns)
                version = dep.find("m:version", ns)
                if artifact_id is not None:
                    name = f"{group_id.text}:{artifact_id.text}" if group_id is not None else artifact_id.text
                    deps.append(FileDependency(
                        name=name or "",
                        version=version.text if version is not None else None,
                        source_file="pom.xml",
                    ))
        except Exception:
            pass
        return deps

    def _parse_gemfile(self, path: str) -> list[FileDependency]:
        """Parse Gemfile."""
        import re
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    match = re.match(r'''gem\s+['"](.+?)['"]''', line.strip())
                    if match:
                        deps.append(FileDependency(
                            name=match.group(1), source_file="Gemfile",
                        ))
        except OSError:
            pass
        return deps

    def _parse_composer_json(self, path: str) -> list[FileDependency]:
        """Parse composer.json."""
        import json
        deps = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            for section in ["require", "require-dev"]:
                dep_dict = data.get(section, {})
                is_dev = section == "require-dev"
                for name, version in dep_dict.items():
                    deps.append(FileDependency(
                        name=name,
                        version=version if isinstance(version, str) else None,
                        is_development=is_dev,
                        source_file="composer.json",
                    ))
        except (json.JSONDecodeError, OSError):
            pass
        return deps
