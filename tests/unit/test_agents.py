"""Tests for analysis agents."""

import asyncio
import pytest
from asa.agents.architecture.agent import ArchitectureAgent
from asa.agents.dependency.agent import DependencyAgent
from asa.agents.documentation.agent import DocumentationAgent
from asa.agents.performance.agent import PerformanceAgent
from asa.agents.reconnaissance.agent import ReconnaissanceAgent
from asa.agents.security.agent import SecurityAgent
from asa.agents.verification.agent import VerificationAgent
from asa.core.evidence import Evidence, Finding
from asa.core.models import (
    DependencyGraph,
    FileAnalysis,
    FunctionInfo,
    ModuleInfo,
    ProjectAnalysis,
    RepositoryInfo,
)
from asa.core.types import NodeType


def make_test_project(
    num_files: int = 3,
    with_test: bool = True,
    with_modules: bool = True,
) -> ProjectAnalysis:
    """Create a minimal test project."""
    files = []
    for i in range(num_files):
        fa = FileAnalysis(
            file_path=f"src/module_{i}.py",
            language="python",
            lines_of_code=100 + i * 50,
            functions=[
                FunctionInfo(
                    name=f"func_{j}",
                    qualified_name=f"module_{i}.func_{j}",
                    symbol_type=NodeType.FUNCTION,
                    location={"file_path": f"src/module_{i}.py", "line_start": j * 10},
                    parameters=[{"name": f"arg_{j}"}],
                )
                for j in range(3)
            ],
        )
        files.append(fa)

    if with_test:
        test_fa = FileAnalysis(
            file_path="tests/test_module.py",
            language="python",
            lines_of_code=50,
            is_test=True,
            functions=[
                FunctionInfo(
                    name="test_func",
                    qualified_name="test_func",
                    symbol_type=NodeType.FUNCTION,
                    location={"file_path": "tests/test_module.py", "line_start": 1},
                )
            ],
        )
        files.append(test_fa)

    modules = []
    if with_modules:
        modules = [
            ModuleInfo(
                name="module_0",
                path="src/module_0",
                files=["src/module_0.py"],
            ),
            ModuleInfo(
                name="module_1",
                path="src/module_1",
                files=["src/module_1.py"],
            ),
        ]

    return ProjectAnalysis(
        repository=RepositoryInfo(
            local_path="/tmp/test-repo",
            name="test-repo",
            total_files=num_files,
            languages={"python": 0.9},
            frameworks=["pytest"],
        ),
        file_analyses=files,
        modules=modules,
        dependency_graph=DependencyGraph(),
    )


class TestReconnaissanceAgent:
    @pytest.mark.asyncio
    async def test_run(self):
        agent = ReconnaissanceAgent()
        project = make_test_project()
        findings = await agent.run(project)

        assert len(findings) > 0
        # Should detect languages
        lang_findings = [f for f in findings if "language" in " ".join(f.tags)]
        assert len(lang_findings) > 0

    @pytest.mark.asyncio
    async def test_detects_size(self):
        agent = ReconnaissanceAgent()
        project = make_test_project(num_files=5)
        findings = await agent.run(project)

        size_findings = [f for f in findings if "size" in " ".join(f.tags)]
        assert len(size_findings) > 0


class TestArchitectureAgent:
    @pytest.mark.asyncio
    async def test_run(self):
        agent = ArchitectureAgent()
        project = make_test_project()
        findings = await agent.run(project)
        assert isinstance(findings, list)

    @pytest.mark.asyncio
    async def test_detects_modules(self):
        agent = ArchitectureAgent()
        project = make_test_project(with_modules=True)
        findings = await agent.run(project)
        module_findings = [f for f in findings if "modules" in " ".join(f.tags) or "architecture" in " ".join(f.tags)]
        assert len(module_findings) > 0


class TestSecurityAgent:
    @pytest.mark.asyncio
    async def test_run_clean_project(self):
        agent = SecurityAgent()
        project = make_test_project()
        findings = await agent.run(project)
        # Clean project should have few or no critical security findings
        critical = [f for f in findings if f.severity.value == "critical"]
        assert len(critical) == 0


class TestPerformanceAgent:
    @pytest.mark.asyncio
    async def test_run(self):
        agent = PerformanceAgent()
        project = make_test_project()
        findings = await agent.run(project)
        assert isinstance(findings, list)


class TestDocumentationAgent:
    @pytest.mark.asyncio
    async def test_run(self):
        agent = DocumentationAgent()
        project = make_test_project()
        findings = await agent.run(project)
        assert isinstance(findings, list)
        # Should check for README
        readme_findings = [f for f in findings if "readme" in " ".join(f.tags)]
        assert len(readme_findings) > 0


class TestVerificationAgent:
    def test_verify_with_evidence(self):
        agent = VerificationAgent()
        finding = Finding(claim="Test claim")
        finding.add_evidence(
            Evidence(
                evidence_type="static_analysis",
                description="Found in source",
                source_file="test.py",
                confidence=0.9,
            )
        )
        from asa.agents.base import AgentTrace
        trace = AgentTrace("verification")

        verified = agent.verify_findings([finding], trace)
        assert len(verified) == 1
        assert verified[0].status in ("verified", "uncertain")

    def test_verify_without_evidence_rejected(self):
        agent = VerificationAgent()
        finding = Finding(claim="Unsupported claim")
        from asa.agents.base import AgentTrace
        trace = AgentTrace("verification")

        verified = agent.verify_findings([finding], trace)
        assert verified[0].status.value == "rejected"
