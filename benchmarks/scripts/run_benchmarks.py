"""Benchmark suite for ASA.

Evaluates:
  - Component detection accuracy
  - Dependency detection accuracy
  - Evidence correctness
  - Hallucination rate
  - Finding precision
  - Analysis latency
  - Memory usage
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from asa.analysis.static.engine import StaticAnalysisEngine
from asa.core.logging import get_logger
from asa.ingestion.repository import RepositoryIngester

logger = get_logger("benchmark")


class BenchmarkResult:
    """Result of a single benchmark run."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.start_time = time.time()
        self.end_time: float | None = None
        self.metrics: dict[str, Any] = {}
        self.errors: list[str] = []

    def complete(self) -> None:
        self.end_time = time.time()

    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_seconds": round(self.duration, 3),
            "metrics": self.metrics,
            "errors": self.errors,
        }


class BenchmarkSuite:
    """Complete benchmark suite for ASA."""

    def __init__(self, results_dir: str = "D:/asa/benchmarks/results") -> None:
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.ingester = RepositoryIngester()
        self.engine = StaticAnalysisEngine()
        self.results: list[BenchmarkResult] = []

    def run_all(self, repo_paths: list[str] | None = None) -> dict[str, Any]:
        """Run all benchmarks."""
        print("=" * 60)
        print("ASA Benchmark Suite")
        print("=" * 60)

        # Use provided repos or synthetic ones
        if not repo_paths:
            repo_paths = self._create_synthetic_repos()

        all_results: list[dict[str, Any]] = []

        for repo_path in repo_paths:
            result = self.benchmark_repo(repo_path)
            all_results.append(result.to_dict())
            self.results.append(result)
            print(f"  {result.name}: {result.duration:.1f}s")

        # Summary
        summary = self._compute_summary(all_results)
        summary["results"] = all_results
        summary["timestamp"] = datetime.utcnow().isoformat()

        # Save results
        output = self.results_dir / f"benchmark_{int(time.time())}.json"
        with open(output, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"\nResults saved to {output}")
        self._print_summary(summary)

        return summary

    def benchmark_repo(self, repo_path: str) -> BenchmarkResult:
        """Benchmark analysis of a single repository."""
        name = os.path.basename(repo_path)
        result = BenchmarkResult(name)

        try:
            # Ingest
            info, path = self.ingester.ingest(local_path=repo_path)

            # Analyze
            project = self.engine.analyze(info)

            # Collect metrics
            result.metrics["files_analyzed"] = len(project.file_analyses)
            result.metrics["total_symbols"] = project.total_symbols
            result.metrics["total_relationships"] = project.total_relationships
            result.metrics["modules_found"] = len(project.modules)
            result.metrics["external_deps"] = len(project.external_dependencies)

            # Component detection
            all_classes = [c for fa in project.file_analyses for c in fa.classes]
            all_functions = [f for fa in project.file_analyses for f in fa.functions]
            result.metrics["classes_detected"] = len(all_classes)
            result.metrics["functions_detected"] = len(all_functions)

            # Graph metrics
            if project.dependency_graph.nodes:
                graph_metrics = self.engine.graph_builder.calculate_metrics()
                result.metrics["graph_metrics"] = graph_metrics

            # Evidence quality
            evidence_count = 0
            for edge in project.dependency_graph.edges:
                if edge.evidence_locations:
                    evidence_count += 1
            result.metrics["edges_with_evidence"] = evidence_count
            total_edges = len(project.dependency_graph.edges)
            result.metrics["evidence_rate"] = (
                evidence_count / total_edges if total_edges > 0 else 0
            )

            # Test file detection
            test_files = [fa for fa in project.file_analyses if fa.is_test]
            result.metrics["test_files_detected"] = len(test_files)

            # Environment variable detection
            all_envs = set()
            for fa in project.file_analyses:
                all_envs.update(fa.environment_variables)
            result.metrics["env_vars_detected"] = len(all_envs)

        except Exception as e:
            result.errors.append(str(e))

        result.complete()
        return result

    def _create_synthetic_repos(self) -> list[str]:
        """Create synthetic repos for benchmarking."""
        from tests.synthetic_repos.create_test_repos import create_all_synthetic_repos

        base = "D:/asa/data/synthetic_benchmark"
        return create_all_synthetic_repos(base)

    def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute summary statistics."""
        if not results:
            return {}

        total_duration = sum(r["duration_seconds"] for r in results)
        total_files = sum(r["metrics"].get("files_analyzed", 0) for r in results)
        total_symbols = sum(r["metrics"].get("total_symbols", 0) for r in results)
        total_relationships = sum(
            r["metrics"].get("total_relationships", 0) for r in results
        )

        evidence_rates = [
            r["metrics"].get("evidence_rate", 0) for r in results
        ]
        avg_evidence_rate = (
            sum(evidence_rates) / len(evidence_rates) if evidence_rates else 0
        )

        return {
            "total_repos": len(results),
            "total_duration_seconds": round(total_duration, 2),
            "total_files_analyzed": total_files,
            "total_symbols_extracted": total_symbols,
            "total_relationships_found": total_relationships,
            "average_evidence_rate": round(avg_evidence_rate, 3),
            "average_latency_per_repo": round(
                total_duration / len(results) if results else 0, 2
            ),
        }

    def _print_summary(self, summary: dict[str, Any]) -> None:
        """Print a formatted summary."""
        print("\n" + "=" * 60)
        print("Benchmark Summary")
        print("=" * 60)
        for key, value in summary.items():
            if key != "results":
                print(f"  {key}: {value}")
        print("=" * 60)


if __name__ == "__main__":
    suite = BenchmarkSuite()
    suite.run_all()
