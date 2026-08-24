"""Main analysis orchestrator.

Coordinates the full analysis pipeline:
  1. Ingest repository
  2. Run static analysis
  3. Build knowledge graph
  4. Run specialized agents
  5. Verify findings
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from asa.analysis.static.engine import StaticAnalysisEngine
from asa.config.settings import Settings, get_settings
from asa.core.logging import get_logger
from asa.core.models import ProjectAnalysis, RepositoryInfo
from asa.ingestion.repository import RepositoryIngester

logger = get_logger("asa.orchestrator")


class AnalysisOrchestrator:
    """Coordinates the end-to-end analysis pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.ingester = RepositoryIngester(self.settings)
        self.static_engine = StaticAnalysisEngine(self.settings)

    async def run_full_analysis(
        self,
        url: str | None = None,
        local_path: str | None = None,
        commit_ref: str | None = None,
        branch: str | None = None,
        phases: list[str] | None = None,
    ) -> ProjectAnalysis:
        """Execute the complete analysis pipeline.

        Args:
            url: GitHub URL to analyze.
            local_path: Local repository path.
            commit_ref: Specific commit to analyze.
            branch: Branch to checkout.
            phases: Optional list of phases to run (default: all).

        Returns:
            Complete ProjectAnalysis with all findings.
        """
        start_time = time.time()
        all_phases = phases or [
            "ingestion", "static_analysis", "knowledge_graph",
            "architecture_inference", "git_history",
        ]

        logger.info("orchestrator.start", url=url, local_path=local_path, phases=all_phases)

        # Phase 1: Repository ingestion
        repo_info: RepositoryInfo | None = None
        repo_path: str = ""
        if "ingestion" in all_phases:
            logger.info("orchestrator.phase", phase="ingestion")
            repo_info, repo_path = self.ingester.ingest(
                url=url, local_path=local_path, commit_ref=commit_ref, branch=branch,
            )
        elif local_path:
            repo_info, repo_path = self.ingester.ingest(local_path=local_path)

        if repo_info is None:
            raise ValueError("Failed to ingest repository")

        # Phase 2: Static analysis
        project: ProjectAnalysis | None = None
        if "static_analysis" in all_phases:
            logger.info("orchestrator.phase", phase="static_analysis")
            project = self.static_engine.analyze(repo_info)
        else:
            project = ProjectAnalysis(repository=repo_info)

        # Phase 3: Git history analysis
        if "git_history" in all_phases:
            logger.info("orchestrator.phase", phase="git_history")
            project.git_history = self.ingester.extract_git_history(repo_path)

        # Phase 4: Knowledge graph (stored in dependency_graph for now)
        if "knowledge_graph" in all_phases:
            logger.info("orchestrator.phase", phase="knowledge_graph")
            # Knowledge graph is built as part of static analysis
            # Future: persist to PostgreSQL

        # Phase 5: Architecture inference
        if "architecture_inference" in all_phases:
            logger.info("orchestrator.phase", phase="architecture_inference")
            # Will be implemented in Phase 3 (agents)

        project.completed_at = datetime.utcnow()
        elapsed = time.time() - start_time

        logger.info(
            "orchestrator.complete",
            elapsed=f"{elapsed:.1f}s",
            files=len(project.file_analyses),
            symbols=project.total_symbols,
            relationships=project.total_relationships,
        )

        return project
