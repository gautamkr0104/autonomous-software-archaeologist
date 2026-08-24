"""Security Agent.

Looks for suspicious architectural/security patterns.
Does NOT claim vulnerabilities without evidence.
"""

from __future__ import annotations

import os
import re
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


# Patterns that indicate potential security concerns
SECURITY_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "hardcoded_secret",
        "pattern": r"""(?:password|secret|api_key|apikey|token|auth_token)\s*=\s*['"][^'"]{8,}['"]""",
        "severity": FindingSeverity.CRITICAL,
        "category": FindingCategory.SECURITY,
        "description": "Possible hardcoded secret or credential",
        "confidence": 0.7,
    },
    {
        "name": "sql_injection_risk",
        "pattern": r"""(?:execute|cursor\.execute)\s*\(\s*['"].*%s.*['"]\s*%""",
        "severity": FindingSeverity.HIGH,
        "category": FindingCategory.SECURITY,
        "description": "Possible SQL injection via string formatting",
        "confidence": 0.8,
    },
    {
        "name": "eval_usage",
        "pattern": r"""\beval\s*\(""",
        "severity": FindingSeverity.MEDIUM,
        "category": FindingCategory.SECURITY,
        "description": "Use of eval() which can execute arbitrary code",
        "confidence": 0.9,
    },
    {
        "name": "exec_usage",
        "pattern": r"""\bexec\s*\(""",
        "severity": FindingSeverity.MEDIUM,
        "category": FindingCategory.SECURITY,
        "description": "Use of exec() which can execute arbitrary code",
        "confidence": 0.9,
    },
    {
        "name": "shell_injection",
        "pattern": r"""os\.system\s*\(|subprocess\.call\s*\(\s*['"]""",
        "severity": FindingSeverity.HIGH,
        "category": FindingCategory.SECURITY,
        "description": "Shell command execution with string — potential injection risk",
        "confidence": 0.7,
    },
    {
        "name": "insecure_random",
        "pattern": r"""\brandom\b\.\b(random|choice|randint)\b(?!\s*#.*crypto)""",
        "severity": FindingSeverity.LOW,
        "category": FindingCategory.SECURITY,
        "description": "Use of non-cryptographic random for potentially sensitive values",
        "confidence": 0.5,
    },
    {
        "name": "debug_mode",
        "pattern": r"""DEBUG\s*=\s*True|debug\s*=\s*True|DEBUG_MODE\s*=\s*['"]?true""",
        "severity": FindingSeverity.LOW,
        "category": FindingCategory.SECURITY,
        "description": "Debug mode enabled — should not be active in production",
        "confidence": 0.6,
    },
    {
        "name": "cors_wildcard",
        "pattern": r"""(?:CORS|cors|Access-Control-Allow-Origin).*\*""",
        "severity": FindingSeverity.MEDIUM,
        "category": FindingCategory.SECURITY,
        "description": "CORS wildcard — allows requests from any origin",
        "confidence": 0.8,
    },
    {
        "name": "disabled_ssl",
        "pattern": r"""verify\s*=\s*False|VERIFY_SSL\s*=\s*False|rejectUnauthorized\s*:\s*false""",
        "severity": FindingSeverity.HIGH,
        "category": FindingCategory.SECURITY,
        "description": "SSL verification disabled — vulnerable to MITM attacks",
        "confidence": 0.85,
    },
    {
        "name": "pickle_load",
        "pattern": r"""pickle\.loads?\s*\(|yaml\.load\s*\([^)]*\)(?!.*Loader)""",
        "severity": FindingSeverity.HIGH,
        "category": FindingCategory.SECURITY,
        "description": "Unsafe deserialization — can execute arbitrary code",
        "confidence": 0.85,
    },
]


class SecurityAgent(BaseAgent):
    """Scans for security-related patterns in the codebase."""

    name = "security"
    description = "Identifies potential security concerns based on code patterns"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []

        findings.extend(self._scan_patterns(project, trace))
        findings.extend(self._check_env_exposure(project, trace))
        findings.extend(self._check_dependency_risks(project, trace))

        return findings

    def _scan_patterns(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Scan source files for security patterns."""
        findings: list[Finding] = []

        for fa in project.file_analyses:
            if fa.is_test or fa.is_config:
                continue

            try:
                file_path = os.path.join(project.repository.local_path, fa.file_path)
                if not os.path.exists(file_path):
                    continue
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            for pattern_def in SECURITY_PATTERNS:
                try:
                    matches = list(re.finditer(pattern_def["pattern"], content, re.IGNORECASE))
                except re.error:
                    continue

                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1
                    # Get surrounding context
                    lines = content.split("\n")
                    context_start = max(0, line_num - 2)
                    context_end = min(len(lines), line_num + 1)
                    snippet = "\n".join(lines[context_start:context_end]).strip()

                    # Redact potential secrets
                    if "secret" in pattern_def["name"] or "password" in pattern_def["name"]:
                        snippet = re.sub(r"(['\"])[^'\"]{8,}(['\"])", r"\1***REDACTED***\2", snippet)

                    findings.append(self._create_finding(
                        claim=f"{pattern_def['description']} in {fa.file_path}",
                        evidence=[
                            self._create_evidence(
                                EvidenceType.STATIC_ANALYSIS,
                                f"Pattern match: {pattern_def['name']}",
                                source_file=fa.file_path,
                                line=line_num,
                                confidence=pattern_def["confidence"],
                                content_snippet=snippet,
                            )
                        ],
                        category=pattern_def["category"],
                        severity=pattern_def["severity"],
                        reasoning=f"Regex pattern match for {pattern_def['name']}. "
                                  f"Confidence is {pattern_def['confidence']:.0%} — verify manually.",
                        source_files=[fa.file_path],
                        tags=["security-scan", pattern_def["name"]],
                    ))

        trace.add_step("pattern_scan", {"findings": len(findings)})
        return findings

    def _check_env_exposure(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Check for exposed environment variables."""
        findings: list[Finding] = []

        # Collect all env vars referenced across the project
        all_env_vars: dict[str, list[str]] = {}
        for fa in project.file_analyses:
            for ev in fa.environment_variables:
                if ev not in all_env_vars:
                    all_env_vars[ev] = []
                all_env_vars[ev].append(fa.file_path)

        # Check for .env files that might be committed
        for fa in project.file_analyses:
            basename = os.path.basename(fa.file_path)
            if basename in (".env", ".env.local", ".env.production", ".env.development"):
                findings.append(self._create_finding(
                    claim=f"Environment file {fa.file_path} is present in the repository",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.CONFIGURATION_VALUE,
                            f"Env file found: {fa.file_path}",
                            source_file=fa.file_path,
                            confidence=0.9,
                        )
                    ],
                    category=FindingCategory.SECURITY,
                    severity=FindingSeverity.HIGH,
                    reasoning="Environment files may contain secrets and should not be committed.",
                    source_files=[fa.file_path],
                    tags=["env-file", "secrets"],
                ))

        if all_env_vars:
            findings.append(self._create_finding(
                claim=f"Repository references {len(all_env_vars)} environment variables",
                evidence=[
                    self._create_evidence(
                        EvidenceType.ENVIRONMENT_VARIABLE,
                        f"Env vars: {', '.join(sorted(all_env_vars.keys())[:20])}",
                        confidence=0.95,
                    )
                ],
                category=FindingCategory.SECURITY,
                severity=FindingSeverity.INFO,
                reasoning="Environment variable references identified for documentation purposes.",
                tags=["environment-variables"],
            ))

        return findings

    def _check_dependency_risks(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Check for dependency-related security risks."""
        findings: list[Finding] = []

        # Known risky packages (simplified)
        risky_packages = {
            "fabric", "paramiko", "subprocess32",  # remote execution
            "pickle", "marshal",  # deserialization
            "requests", "urllib3",  # HTTP (not risky per se, but note)
        }

        for dep in project.external_dependencies:
            if dep.name.lower() in risky_packages:
                findings.append(self._create_finding(
                    claim=f"Dependency '{dep.name}' has known security considerations",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.DEPENDENCY_DECLARATION,
                            f"Package {dep.name} ({dep.version or 'unknown'}) has security implications",
                            source_file=dep.source_file,
                            confidence=0.5,
                        )
                    ],
                    category=FindingCategory.SECURITY,
                    severity=FindingSeverity.LOW,
                    reasoning="Note: this is informational. Check CVE databases for specific vulnerabilities.",
                    tags=["dependency-risk", dep.name],
                ))

        return findings
