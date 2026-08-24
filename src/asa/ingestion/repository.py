"""Repository ingestion service.

Handles cloning, metadata extraction, language detection, framework detection,
file classification, and git history extraction.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from asa.config.settings import Settings, get_settings
from asa.core.logging import get_logger
from asa.core.models import CommitInfo, GitHistory, RepositoryInfo
from asa.core.utils import (
    BINARY_EXTENSIONS,
    SKIP_DIRS,
    detect_language,
    is_binary_file,
    should_skip_dir,
)

logger = get_logger("asa.ingestion")

# Framework detection patterns
FRAMEWORK_PATTERNS: dict[str, dict[str, list[str]]] = {
    "python": {
        "django": ["manage.py", "settings.py", "wsgi.py", "asgi.py"],
        "fastapi": ["main.py"],
        "flask": ["app.py", "wsgi.py"],
        "pytest": ["conftest.py", "pytest.ini"],
        "celery": ["celery.py", "tasks.py"],
    },
    "javascript": {
        "react": ["jsx", "tsx", "react"],
        "next": ["next.config", "pages", "app"],
        "vue": ["vue.config", ".vue"],
        "svelte": ["svelte.config"],
        "express": ["express", "app.js", "server.js"],
        "nestjs": ["nest", "module.ts"],
        "angular": ["angular.json"],
    },
    "typescript": {
        "next": ["next.config"],
        "nestjs": ["nest-cli.json"],
        "angular": ["angular.json"],
    },
    "java": {
        "spring": ["pom.xml", "build.gradle"],
        "maven": ["pom.xml"],
        "gradle": ["build.gradle"],
    },
    "go": {
        "gin": ["gin"],
        "echo": ["echo"],
        "fiber": ["fiber"],
    },
    "rust": {
        "actix": ["actix-web"],
        "axum": ["axum"],
        "rocket": ["rocket"],
    },
}


class RepositoryIngester:
    """Clones and performs initial analysis of a repository."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.repos_dir.mkdir(parents=True, exist_ok=True)

    def ingest(
        self,
        url: str | None = None,
        local_path: str | None = None,
        commit_ref: str | None = None,
        branch: str | None = None,
    ) -> tuple[RepositoryInfo, str]:
        """Ingest a repository and return metadata + local path.

        Args:
            url: GitHub URL to clone.
            local_path: Path to a local repository.
            commit_ref: Specific commit to analyze.
            branch: Branch to checkout.

        Returns:
            Tuple of (RepositoryInfo, local_path).
        """
        if url:
            repo_path = self._clone(url, branch=branch)
        elif local_path:
            repo_path = self._prepare_local(local_path)
        else:
            raise ValueError("Must provide either url or local_path")

        # Checkout specific commit if requested
        if commit_ref:
            self._checkout(repo_path, commit_ref)

        # Extract metadata
        info = self._extract_metadata(repo_path, url=url, commit_ref=commit_ref)

        logger.info(
            "ingestion.complete",
            name=info.name,
            languages=info.languages,
            files=info.total_files,
            commits=info.commit_count,
        )

        return info, repo_path

    def _clone(self, url: str, branch: str | None = None) -> str:
        """Clone a git repository."""
        # Derive path from URL
        repo_name = url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        repo_path = str(self.settings.repos_dir / repo_name)

        # Remove existing clone
        if os.path.exists(repo_path):
            import shutil
            shutil.rmtree(repo_path, ignore_errors=True)

        cmd = ["git", "clone", "--depth=1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([url, repo_path])

        logger.info("ingestion.cloning", url=url, path=repo_path)

        start = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.settings.clone_timeout,
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            # Try full clone if shallow fails
            cmd_full = ["git", "clone", url, repo_path]
            if branch:
                cmd_full = ["git", "clone", "--branch", branch, url, repo_path]
            result = subprocess.run(
                cmd_full,
                capture_output=True,
                text=True,
                timeout=self.settings.clone_timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to clone {url}: {result.stderr}")

        logger.info("ingestion.clone_complete", elapsed=f"{elapsed:.1f}s", path=repo_path)
        return repo_path

    def _prepare_local(self, local_path: str) -> str:
        """Validate and prepare a local repository."""
        path = os.path.abspath(local_path)
        if not os.path.isdir(path):
            raise ValueError(f"Not a directory: {path}")
        git_dir = os.path.join(path, ".git")
        if not os.path.exists(git_dir):
            logger.warning("ingestion.not_git_repo", path=path)
        return path

    def _checkout(self, repo_path: str, ref: str) -> None:
        """Checkout a specific commit or branch."""
        result = subprocess.run(
            ["git", "checkout", ref],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to checkout {ref}: {result.stderr}")

    def _extract_metadata(
        self,
        repo_path: str,
        url: str | None = None,
        commit_ref: str | None = None,
    ) -> RepositoryInfo:
        """Extract repository metadata."""
        name = os.path.basename(repo_path)

        # Count files and detect languages
        language_bytes: dict[str, int] = {}
        total_files = 0
        total_size = 0

        for root, dirs, files in os.walk(repo_path):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]

            rel_root = os.path.relpath(root, repo_path)

            for filename in files:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)

                if is_binary_file(file_path):
                    continue

                lang = detect_language(rel_path)
                if lang is None:
                    continue

                try:
                    size = os.path.getsize(file_path)
                    language_bytes[lang] = language_bytes.get(lang, 0) + size
                    total_size += size
                    total_files += 1
                except OSError:
                    continue

                # Limit file count
                if total_files >= self.settings.max_files_analyzed:
                    break

            if total_files >= self.settings.max_files_analyzed:
                break

        # Calculate language percentages
        total_bytes = sum(language_bytes.values()) or 1
        languages = {
            lang: round(bytes_count / total_bytes, 4)
            for lang, bytes_count in sorted(
                language_bytes.items(), key=lambda x: -x[1]
            )
        }

        # Detect frameworks
        frameworks = self._detect_frameworks(repo_path, languages)

        # Git metadata
        git_info = self._get_git_info(repo_path)

        # README
        description = self._read_description(repo_path)

        return RepositoryInfo(
            url=url,
            local_path=repo_path,
            name=name,
            description=description,
            default_branch=git_info.get("default_branch", "main"),
            languages=languages,
            frameworks=frameworks,
            total_files=total_files,
            total_size_bytes=total_size,
            commit_count=git_info.get("commit_count", 0),
            first_commit=git_info.get("first_commit"),
            last_commit=git_info.get("last_commit"),
            analyzed_at=datetime.utcnow(),
            commit_ref=commit_ref,
        )

    def _detect_frameworks(self, repo_path: str, languages: dict[str, float]) -> list[str]:
        """Detect frameworks based on file patterns."""
        detected: list[str] = []

        for lang, patterns in FRAMEWORK_PATTERNS.items():
            if lang not in languages:
                continue

            for framework, markers in patterns.items():
                for marker in markers:
                    # Check for marker in filenames
                    for root, dirs, files in os.walk(repo_path):
                        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
                        for f in files:
                            if marker.lower() in f.lower():
                                if framework not in detected:
                                    detected.append(framework)
                                break

                        # Check for marker in filenames content
                        for f in files:
                            fpath = os.path.join(root, f)
                            if os.path.getsize(fpath) > 1_000_000:
                                continue
                            try:
                                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                                    content = fh.read(50_000)
                                    if marker.lower() in content.lower():
                                        if framework not in detected:
                                            detected.append(framework)
                                        break
                            except OSError:
                                continue

        return detected

    def _get_git_info(self, repo_path: str) -> dict[str, Any]:
        """Extract git repository information."""
        info: dict[str, Any] = {}

        # Default branch
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            info["default_branch"] = result.stdout.strip().replace("origin/", "")
        else:
            info["default_branch"] = "main"

        # Commit count
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            try:
                info["commit_count"] = int(result.stdout.strip())
            except ValueError:
                info["commit_count"] = 0

        # First commit date
        result = subprocess.run(
            ["git", "log", "--reverse", "--format=%aI", "-1"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                info["first_commit"] = datetime.fromisoformat(result.stdout.strip())
            except ValueError:
                pass

        # Last commit date
        result = subprocess.run(
            ["git", "log", "--format=%aI", "-1"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                info["last_commit"] = datetime.fromisoformat(result.stdout.strip())
            except ValueError:
                pass

        return info

    def _read_description(self, repo_path: str) -> str | None:
        """Try to read a description from README or similar."""
        for readme in ["README.md", "README.rst", "README.txt", "README"]:
            path = os.path.join(repo_path, readme)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        # Skip title line, get first non-empty paragraph
                        for line in lines[1:20]:
                            stripped = line.strip()
                            if stripped and not stripped.startswith("#"):
                                return stripped[:200]
                except OSError:
                    continue
        return None

    def extract_git_history(
        self,
        repo_path: str,
        max_commits: int = 500,
        since: str | None = None,
        until: str | None = None,
    ) -> GitHistory:
        """Extract git history for the repository."""
        commits: list[CommitInfo] = []
        contributors: dict[str, int] = {}

        cmd = [
            "git", "log",
            f"--max-count={max_commits}",
            "--format=%H|%s|%an|%ae|%aI",
            "--numstat",
        ]
        if since:
            cmd.append(f"--since={since}")
        if until:
            cmd.append(f"--until={until}")

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.warning("ingestion.git_history_failed", error=result.stderr)
            return GitHistory()

        current_commit: dict[str, Any] | None = None
        files_changed: list[str] = []
        insertions = 0
        deletions = 0

        for line in result.stdout.split("\n"):
            line = line.strip()
            if not line:
                if current_commit:
                    current_commit["files"] = files_changed
                    current_commit["insertions"] = insertions
                    current_commit["deletions"] = deletions
                    commits.append(CommitInfo(**current_commit))
                    current_commit = None
                    files_changed = []
                    insertions = 0
                    deletions = 0
                continue

            if "|" in line and len(line.split("|")) == 5:
                parts = line.split("|")
                sha, message, author, email, date_str = parts
                try:
                    date = datetime.fromisoformat(date_str)
                except ValueError:
                    date = datetime.utcnow()
                current_commit = {
                    "sha": sha,
                    "message": message,
                    "author": author,
                    "author_email": email,
                    "date": date,
                }
                contributors[author] = contributors.get(author, 0) + 1
            elif "\t" in line:
                parts = line.split("\t")
                if len(parts) == 3:
                    files_changed.append(parts[2])
                    try:
                        insertions += int(parts[0]) if parts[0] != "-" else 0
                        deletions += int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        pass

        # Last commit
        if current_commit:
            current_commit["files"] = files_changed
            current_commit["insertions"] = insertions
            current_commit["deletions"] = deletions
            commits.append(CommitInfo(**current_commit))

        # Branches
        branches: list[str] = []
        result = subprocess.run(
            ["git", "branch", "-a", "--format=%(refname:short)"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]

        # Tags
        tags: list[str] = []
        result = subprocess.run(
            ["git", "tag", "--list"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]

        return GitHistory(
            commits=commits,
            branches=branches,
            tags=tags,
            contributors=contributors,
        )
