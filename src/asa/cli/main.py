"""ASA CLI — main entry point.

Commands:
    asa analyze <repo>          Analyze a repository
    asa compare <c1> <c2>       Compare two commits (Architecture Autopsy)
    asa report                  Generate report for last analysis
    asa serve                   Start the web interface
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

app = typer.Typer(
    name="asa",
    help="Autonomous Software Archaeologist — reconstructs how software works.",
    add_completion=False,
)
console = Console()

# Sub-commands as groups
analyze_app = typer.Typer(help="Analyze repositories")
app.add_typer(analyze_app, name="analyze")


@app.command()
def analyze(
    source: str = typer.Argument(..., help="GitHub URL or local path"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch to analyze"),
    commit: Optional[str] = typer.Option(None, "--commit", "-c", help="Specific commit"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file (JSON)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Analyze a GitHub repository or local path."""
    from asa.config.settings import get_settings
    from asa.core.orchestrator import AnalysisOrchestrator

    settings = get_settings()
    if verbose:
        settings.log_level = "DEBUG"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing repository...", total=None)

        orchestrator = AnalysisOrchestrator(settings)

        # Determine if source is URL or local path
        url = None
        local_path = None
        if source.startswith("http") or source.startswith("git@"):
            url = source
        else:
            local_path = source

        progress.update(task, description="📥 Ingesting repository...")

        # Run the analysis
        start = time.time()
        project = asyncio.run(
            orchestrator.run_full_analysis(
                url=url, local_path=local_path, commit_ref=commit, branch=branch,
            )
        )
        elapsed = time.time() - start

    # Display results
    console.print()
    _display_summary(project, elapsed)

    # Save output
    if output:
        output_path = Path(output)
        data = project.model_dump()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"\n[green]✓[/green] Results saved to {output_path}")


@app.command()
def compare(
    repo: str = typer.Argument(..., help="Repository path"),
    commit_a: str = typer.Argument(..., help="Old commit hash"),
    commit_b: str = typer.Argument(..., help="New commit hash"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """Compare two commits — Architecture Autopsy."""
    from asa.config.settings import get_settings
    from asa.core.orchestrator import AnalysisOrchestrator

    settings = get_settings()

    console.print(Panel(
        f"[bold]Architecture Autopsy[/bold]\n"
        f"Comparing {commit_a[:8]}... → {commit_b[:8]}...",
        title="🔍 ASA Compare",
    ))

    orchestrator = AnalysisOrchestrator(settings)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing old commit...", total=None)

        progress.update(task, description="📥 Analyzing old commit...")
        project_a = asyncio.run(
            orchestrator.run_full_analysis(local_path=repo, commit_ref=commit_a)
        )

        progress.update(task, description="📥 Analyzing new commit...")
        project_b = asyncio.run(
            orchestrator.run_full_analysis(local_path=repo, commit_ref=commit_b)
        )

    # Compare results
    _display_comparison(project_a, project_b, commit_a, commit_b)

    if output:
        output_path = Path(output)
        data = {
            "commit_a": commit_a,
            "commit_b": commit_b,
            "before": project_a.model_dump(),
            "after": project_b.model_dump(),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"\n[green]✓[/green] Comparison saved to {output_path}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload", "-r"),
) -> None:
    """Start the ASA web server."""
    import uvicorn
    console.print(Panel(
        f"[bold]ASA Web Interface[/bold]\n"
        f"Starting on http://{host}:{port}",
        title="🌐 ASA Serve",
    ))
    uvicorn.run(
        "asa.api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@app.command()
def status() -> None:
    """Show system status and capabilities."""
    from asa.analysis.parsers.tree_sitter_parser import TreeSitterParser

    parser = TreeSitterParser()

    table = Table(title="ASA System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row("Tree-sitter Parser", "✓" if parser.available_languages else "✗",
                   f"{len(parser.available_languages)} languages available")
    table.add_row("Repository Ingestion", "✓", "Git clone, local repos")
    table.add_row("Static Analysis", "✓", "AST parsing, symbol extraction")
    table.add_row("Dependency Graph", "✓", "Import, call, inheritance analysis")
    table.add_row("Knowledge Graph", "✓", "In-memory graph store")
    table.add_row("Web Interface", "✓", "FastAPI + React")

    console.print(table)

    if parser.available_languages:
        console.print(f"\n[bold]Supported languages:[/bold] {', '.join(sorted(parser.available_languages))}")


def _display_summary(project: ProjectAnalysis, elapsed: float) -> None:
    """Display analysis summary."""
    from asa.core.evidence import ConfidenceLevel

    console.print(Panel(
        f"[bold]{project.repository.name}[/bold]",
        title="📊 Analysis Complete",
    ))

    # Overview table
    table = Table(title="Repository Overview", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Files Analyzed", str(len(project.file_analyses)))
    table.add_row("Total Symbols", str(project.total_symbols))
    table.add_row("Relationships", str(project.total_relationships))
    table.add_row("Modules", str(len(project.modules)))
    table.add_row("External Dependencies", str(len(project.external_dependencies)))
    table.add_row("Git Commits", str(len(project.git_history.commits)))
    table.add_row("Analysis Time", f"{elapsed:.1f}s")

    console.print(table)

    # Language breakdown
    if project.repository.languages:
        console.print("\n[bold]Languages:[/bold]")
        for lang, pct in list(project.repository.languages.items())[:10]:
            bar = "█" * int(pct * 30) + "░" * (30 - int(pct * 30))
            console.print(f"  {lang:15s} {bar} {pct*100:.1f}%")

    # Frameworks
    if project.repository.frameworks:
        console.print(f"\n[bold]Frameworks:[/bold] {', '.join(project.repository.frameworks)}")

    # Graph metrics
    if project.dependency_graph.nodes:
        graph = project.dependency_graph
        console.print(f"\n[bold]Dependency Graph:[/bold]")
        console.print(f"  Nodes: {len(graph.nodes)}")
        console.print(f"  Edges: {len(graph.edges)}")
        console.print(f"  Fan-in (max): {graph.fan_in(list(graph.nodes.keys())[0]) if graph.nodes else 0}")

    # Phase results
    if project.phase_results:
        console.print(f"\n[bold]Analysis Phases:[/bold]")
        for pr in project.phase_results:
            status_icon = "✓" if pr.status == "completed" else "✗"
            dur = f" ({pr.duration_seconds:.1f}s)" if pr.duration_seconds else ""
            console.print(f"  {status_icon} {pr.phase.value}{dur}")


def _display_comparison(
    before: ProjectAnalysis,
    after: ProjectAnalysis,
    commit_a: str,
    commit_b: str,
) -> None:
    """Display Architecture Autopsy comparison."""
    console.print(Panel(
        f"[bold]Architecture Autopsy Report[/bold]\n\n"
        f"Before: {commit_a[:8]}...\n"
        f"After:  {commit_b[:8]}...",
        title="🔍 Comparison",
    ))

    table = Table(title="Changes")
    table.add_column("Metric", style="cyan")
    table.add_column("Before", style="dim")
    table.add_column("After", style="white")
    table.add_column("Delta", style="bold")

    def _delta(a: int, b: int) -> str:
        d = b - a
        if d > 0:
            return f"[green]+{d}[/green]"
        elif d < 0:
            return f"[red]{d}[/red]"
        return "[dim]0[/dim]"

    table.add_row("Files", str(len(before.file_analyses)), str(len(after.file_analyses)),
                   _delta(len(before.file_analyses), len(after.file_analyses)))
    table.add_row("Symbols", str(before.total_symbols), str(after.total_symbols),
                   _delta(before.total_symbols, after.total_symbols))
    table.add_row("Relationships", str(before.total_relationships), str(after.total_relationships),
                   _delta(before.total_relationships, after.total_relationships))
    table.add_row("Modules", str(len(before.modules)), str(len(after.modules)),
                   _delta(len(before.modules), len(after.modules)))

    console.print(table)

    # Dependency changes
    before_deps = {e.target_id for e in before.dependency_graph.edges}
    after_deps = {e.target_id for e in after.dependency_graph.edges}
    new_deps = after_deps - before_deps
    removed_deps = before_deps - after_deps

    if new_deps:
        console.print(f"\n[bold green]New dependencies ({len(new_deps)}):[/bold green]")
        for dep in list(new_deps)[:10]:
            console.print(f"  + {dep}")

    if removed_deps:
        console.print(f"\n[bold red]Removed dependencies ({len(removed_deps)}):[/bold red]")
        for dep in list(removed_deps)[:10]:
            console.print(f"  - {dep}")


if __name__ == "__main__":
    app()
