"""Security validation for repository analysis.

Treats analyzed repositories as untrusted input.
Implements path traversal protection, secret redaction, and malicious file detection.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from asa.core.logging import get_logger
from asa.core.utils import BINARY_EXTENSIONS

logger = get_logger("asa.security")


class PathTraversalProtector:
    """Prevents path traversal attacks from repository files."""

    FORBIDDEN_PATTERNS = [
        "..",
        "~",
        "/etc/",
        "/proc/",
        "/sys/",
        "\\..\\",
        "C:\\",
        "D:\\",
    ]

    @staticmethod
    def validate_path(file_path: str, base_dir: str) -> bool:
        """Check if a file path stays within the base directory."""
        try:
            resolved = os.path.realpath(os.path.join(base_dir, file_path))
            base_real = os.path.realpath(base_dir)
            return resolved.startswith(base_real)
        except (ValueError, OSError):
            return False

    @staticmethod
    def sanitize_path(file_path: str) -> str:
        """Remove dangerous path components."""
        # Remove leading slashes and backslashes
        path = file_path.lstrip("/").lstrip("\\")
        # Remove traversal components
        parts = Path(path).parts
        safe_parts = [p for p in parts if p not in (".", "..", "~")]
        return str(Path(*safe_parts)) if safe_parts else ""


class SecretRedactor:
    """Redacts potential secrets from analysis output."""

    PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"""(?:password|passwd|pwd)\s*[=:]\s*['"]([^'"]+)['"]""", re.I),
        re.compile(r"""(?:secret|secret_key|secret_key_base)\s*[=:]\s*['"]([^'"]+)['"]""", re.I),
        re.compile(r"""(?:api_key|apikey|api-key)\s*[=:]\s*['"]([^'"]+)['"]""", re.I),
        re.compile(r"""(?:token|auth_token|access_token)\s*[=:]\s*['"]([^'"]+)['"]""", re.I),
        re.compile(r"""(?:AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['"]([^'"]+)['"]""", re.I),
        re.compile(r"""(?:PRIVATE KEY)-----""", re.I),
        re.compile(r"""Bearer\s+[A-Za-z0-9\-._~+/]+=*""", re.I),
        re.compile(r"""ghp_[A-Za-z0-9]{36}"""),  # GitHub PAT
        re.compile(r"""sk-[A-Za-z0-9]{32,}"""),  # OpenAI API key
        re.compile(r"""xox[baprs]-[A-Za-z0-9\-]+"""),  # Slack token
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        """Redact potential secrets from text."""
        redacted = text
        for pattern in cls.PATTERNS:
            redacted = pattern.sub(
                lambda m: m.group(0).replace(m.group(1), "***REDACTED***") if m.lastindex else "***REDACTED***",
                redacted,
            )
        return redacted

    @classmethod
    def contains_secrets(cls, text: str) -> bool:
        """Check if text likely contains secrets."""
        for pattern in cls.PATTERNS:
            if pattern.search(text):
                return True
        return False


class MaliciousFileDetector:
    """Detects potentially malicious files in repositories."""

    # Dangerous file patterns
    DANGEROUS_FILENAMES = [
        ".bashrc", ".bash_profile", ".profile", ".zshrc",
        ".gitconfig", ".ssh/config",
        "Makefile",  # can contain arbitrary commands
    ]

    # Content patterns that suggest malicious intent
    DANGEROUS_PATTERNS = [
        re.compile(r"""curl\s+.*\|\s*(?:bash|sh)"""),  # curl | bash
        re.compile(r"""wget\s+.*\|\s*(?:bash|sh)"""),  # wget | bash
        re.compile(r"""rm\s+-rf\s+/"""),  # rm -rf /
        re.compile(r"""\beval\b.*\$(?:\(.*\)|\{.*\})"""),  # eval with command substitution
        re.compile(r"""base64\s+-d"""),  # base64 decode
        re.compile(r"""\\x[0-9a-fA-F]{2}"""),  # hex encoded bytes
    ]

    @classmethod
    def scan_file(cls, file_path: str, content: str | None = None) -> dict[str, Any]:
        """Scan a file for potentially malicious content."""
        result: dict[str, Any] = {
            "safe": True,
            "warnings": [],
            "risk_level": "low",
        }

        basename = os.path.basename(file_path)

        # Check filename
        if basename in cls.DANGEROUS_FILENAMES:
            result["warnings"].append(f"Potentially dangerous file: {basename}")
            result["risk_level"] = "medium"

        # Check for shell scripts in unexpected places
        if file_path.endswith((".sh", ".bash")) and "script" not in file_path.lower():
            result["warnings"].append(f"Shell script found: {file_path}")
            result["risk_level"] = max(result["risk_level"], "medium")

        # Content checks
        if content:
            for pattern in cls.DANGEROUS_PATTERNS:
                if pattern.search(content):
                    result["warnings"].append(
                        f"Dangerous pattern found: {pattern.pattern[:50]}..."
                    )
                    result["risk_level"] = "high"
                    result["safe"] = False

        # Check for binary files that shouldn't be there
        ext = os.path.splitext(file_path)[1].lower()
        if ext in {".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1"}:
            result["warnings"].append(f"Executable/binary file: {file_path}")
            result["risk_level"] = "high"
            result["safe"] = False

        return result

    @classmethod
    def scan_repository(cls, repo_path: str, max_files: int = 1000) -> list[dict[str, Any]]:
        """Scan a repository for malicious files."""
        from asa.core.utils import should_skip_dir

        warnings: list[dict[str, Any]] = []
        count = 0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]

            for filename in files:
                if count >= max_files:
                    break

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)

                result = cls.scan_file(rel_path)
                if result["warnings"]:
                    warnings.append({
                        "file": rel_path,
                        **result,
                    })

                count += 1

            if count >= max_files:
                break

        return warnings


class ResourceLimiter:
    """Enforces resource limits during repository analysis."""

    def __init__(
        self,
        max_repo_size_mb: int = 500,
        max_file_size_mb: int = 50,
        max_files: int = 10_000,
        max_total_size_mb: int = 1000,
    ) -> None:
        self.max_repo_size_mb = max_repo_size_mb
        self.max_file_size_mb = max_file_size_mb
        self.max_files = max_files
        self.max_total_size_mb = max_total_size_mb

    def check_repo_size(self, repo_path: str) -> tuple[bool, str]:
        """Check if repository is within size limits."""
        total_size = 0
        file_count = 0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for f in files:
                file_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                    file_count += 1
                except OSError:
                    continue

                if file_count > self.max_files:
                    return False, f"Too many files ({file_count} > {self.max_files})"
                if total_size > self.max_total_size_mb * 1024 * 1024:
                    return False, f"Repository too large ({total_size / 1024 / 1024:.1f} MB)"

        return True, f"OK ({file_count} files, {total_size / 1024 / 1024:.1f} MB)"

    def check_file_size(self, file_path: str) -> bool:
        """Check if a file is within size limits."""
        try:
            size = os.path.getsize(file_path)
            return size <= self.max_file_size_mb * 1024 * 1024
        except OSError:
            return False
