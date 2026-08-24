#!/bin/bash
# ASA Demo — analyze a sample repository
set -e

echo "=== ASA Demo ==="
echo ""

# Analyze the ASA repo itself as a demo
echo "Analyzing a sample repository..."
echo ""

# Option 1: Analyze a local sample
python -c "
import asyncio
from asa.core.orchestrator import AnalysisOrchestrator

async def main():
    orchestrator = AnalysisOrchestrator()
    project = await orchestrator.run_full_analysis(
        local_path='D:/asa'
    )
    
    print(f'Repository: {project.repository.name}')
    print(f'Files analyzed: {len(project.file_analyses)}')
    print(f'Total symbols: {project.total_symbols}')
    print(f'Relationships: {project.total_relationships}')
    print(f'Modules: {len(project.modules)}')
    print(f'External deps: {len(project.external_dependencies)}')
    
    print()
    print('Languages:')
    for lang, pct in project.repository.languages.items():
        print(f'  {lang}: {pct*100:.1f}%')
    
    print()
    print('Graph metrics:')
    metrics = orchestrator.static_engine.graph_builder.calculate_metrics()
    for key, value in list(metrics.items())[:5]:
        print(f'  {key}: {value}')

asyncio.run(main())
"

echo ""
echo "=== Demo Complete ==="
