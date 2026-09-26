<h1 align="center">ASA — Autonomous Software Archaeologist</h1>

<p align="center">
  <strong>Reconstructs how software works from repositories — with evidence, not assumptions.</strong>
</p>

<p align="center">
  <a href="https://github.com/gautamkr0104/asa/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+" /></a>
  <a href="https://github.com/gautamkr0104/asa/actions"><img src="https://img.shields.io/github/actions/workflow/status/gautamkr0104/asa/ci.yml?branch=main" alt="CI" /></a>
  <a href="https://github.com/gautamkr0104/asa"><img src="https://img.shields.io/github/stars/gautamkr0104/asa?style=social" alt="Stars" /></a>
</p>

---

ASA accepts a GitHub repository (or local path) and **autonomously reconstructs** how the software works. It produces a persistent, evidence-backed model containing components, dependencies, execution paths, APIs, data flows, architectural boundaries, and more — with **machine-verifiable evidence** for every conclusion.

## Table of Contents

- [Highlights](#highlights)
- [Architecture](#architecture)
- [Core Principle](#core-principle)
- [Quick Start](#quick-start)
- [CLI Commands](#cli-commands)
- [Features](#features)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Development](#development)
- [Roadmap](#roadmap)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)
- [Credits](#credits)

---

## Highlights

- 🔍 **Tree-sitter parsing** for 20+ programming languages
- 🤖 **Autonomous analysis agents** — reconnaissance, architecture, dependency, history, security, performance, documentation, verification
- 🧠 **Knowledge graph** with in-memory, PostgreSQL, and Neo4j backends
- ✅ **Evidence system** — every finding is backed by machine-verifiable proof with confidence scoring
- 🛡️ **Security-first sandboxing** — Docker isolation, path traversal protection, secret redaction
- 🌐 **Web interface** — interactive architecture graphs, code explorer, AI investigation
- 📊 **Architecture Autopsy** — compare commits to understand architectural evolution

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                       ASA Architecture                         │
├───────────────────────────────────────────────────────────────┤
│  ┌────────────┐   ┌────────────┐   ┌───────────────────────┐ │
│  │   CLI /    │   │  REST API  │   │  GitHub Integration   │ │
│  │   Web UI   │──▶│  (FastAPI) │   │                       │ │
│  └────────────┘   └─────┬──────┘   └───────────────────────┘ │
│                         │                                      │
│  ┌──────────────────────▼──────────────────────────────────┐  │
│  │                Analysis Orchestrator                     │  │
│  └───┬────────────────┬────────────────┬──────────────────┘  │
│      │                │                │                       │
│  ┌───▼────┐    ┌──────▼──────┐  ┌─────▼────────────────┐    │
│  │Ingestion│    │   Static    │  │  Autonomous Agents   │    │
│  │ Service │    │   Analysis  │  │  ┌────────────────┐  │    │
│  │         │    │   Engine    │  │  │ Reconnaissance  │  │    │
│  │• Clone  │    │             │  │  │ Architecture    │  │    │
│  │• Lang   │    │• Tree-Sitter│  │  │ Dependency      │  │    │
│  │  Detect │    │  Parsers   │  │  │ History         │  │    │
│  │• Git    │    │• Extractors│  │  │ Security        │  │    │
│  │  History│    │• Graph     │  │  │ Performance     │  │    │
│  │         │    │  Builder   │  │  │ Documentation   │  │    │
│  └─────────┘    └─────┬──────┘  │  │ Verification    │  │    │
│                       │          │  └────────────────┘  │    │
│  ┌────────────────────▼──────────┴──────────────────────┐    │
│  │              Knowledge Graph                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │ In-Memory│  │PostgreSQL│  │   Neo4j (opt)     │   │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            Evidence System                            │    │
│  │  claim → evidence → source → confidence → analyzer    │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            Security Layer                             │    │
│  │  Docker isolation · path protection · secret redact   │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

---

## Core Principle

> **NEVER allow an LLM to make an architectural claim without attempting to attach machine-verifiable evidence.**

Every finding produced by ASA includes:

| Field | Description |
|-------|-------------|
| `claim` | What was concluded |
| `evidence` | Machine-verifiable proof |
| `source files` | Where the evidence was found |
| `source locations` | Precise line numbers (when available) |
| `reasoning` | How the conclusion was reached |
| `confidence score` | 0.0 – 1.0 |
| `analyzer` | Which agent produced the finding |

---

## Quick Start

### Prerequisites

| Dependency | Version |
|------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Git | latest |

### Installation

```bash
# Clone the repository
git clone https://github.com/gautamkr0104/asa.git
cd asa

# Install Python dependencies
pip install -e ".[dev]"

# Install optional extras
pip install -e ".[neo4j]"    # Neo4j backend
pip install -e ".[llm]"      # LLM-powered reasoning
pip install -e ".[benchmark]" # Benchmark suite

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Analyze a Repository

```bash
# From a GitHub URL
asa analyze https://github.com/example/project

# From a local path
asa analyze ./local-repo

# Analyze a specific commit
asa analyze https://github.com/example/project --commit abc123

# Compare two commits (Architecture Autopsy)
asa compare ./repo abc123 def456
```

### Launch the Web Interface

```bash
asa serve
# Open http://localhost:8000 in your browser
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `asa analyze <source>` | Analyze a GitHub URL or local path |
| `asa compare <repo> <old> <new>` | Compare two commits for architectural evolution |
| `asa serve` | Start the web interface (FastAPI + React) |
| `asa status` | Show system status and health |
| `asa report` | Generate a formatted analysis report |

---

## Features

### Static Analysis Engine

- **Tree-sitter AST parsing** for 20+ languages (Python, JS/TS, Go, Rust, Java, C/C++, Ruby, etc.)
- Language-aware symbol and import extraction
- Dependency graph construction with circular dependency detection
- Configuration and environment variable detection
- Regex-based fallback analysis for unsupported languages

### Autonomous Analysis Agents

| Agent | Purpose |
|-------|---------|
| **Reconnaissance** | Determines repository contents and structure |
| **Architecture** | Infers components, boundaries, and design patterns |
| **Dependency** | Analyzes coupling, modularity, and structure |
| **History** | Maps git evolution, author patterns, and churn |
| **Security** | Pattern-based vulnerability and secret scanning |
| **Performance** | Identifies potential bottlenecks and anti-patterns |
| **Documentation** | Measures documentation coverage and quality |
| **Verification** | Validates all findings — **hallucination resistance** |

### Knowledge Graph

- **Entity types:** Repository, Commit, File, Module, Class, Function, API, Database, ExternalService, Configuration, Test
- **Relationship types:** CONTAINS, IMPORTS, CALLS, INHERITS, IMPLEMENTS, EXPOSES, CONSUMES, PUBLISHES, READS_FROM, WRITES_TO, TESTED_BY, DEPENDS_ON, EVIDENCED_BY
- **Graph metrics:** fan-in, fan-out, centrality, cycles, connected components
- **Backends:** In-memory (default), PostgreSQL, Neo4j (optional)

### Evidence System

- Every finding backed by machine-verifiable evidence
- Confidence scoring based on evidence quality and diversity
- Verification agent rejects unsupported claims
- Evidence chains for tracing the reasoning path

### Interactive Web Interface

| View | What it shows |
|------|---------------|
| **Overview** | Repository summary, languages, risk summary |
| **Architecture Graph** | Interactive dependency visualization |
| **Code Explorer** | Browse files, symbols, and relationships |
| **Findings** | Filter and verify evidence-backed findings |
| **AI Investigation** | Ask natural-language questions about the codebase |

### Architecture Autopsy

Compare two commits to understand architectural evolution:

- Dependency graph changes
- Module boundary shifts
- Complexity metrics
- Coupling changes
- Commit churn analysis

### Security

- Docker-based repository isolation
- Path traversal protection
- Secret redaction in all outputs
- Resource limits (file count, size, memory)
- Malicious file detection
- No host credential exposure

---

## Docker

### Docker Compose (recommended)

```bash
cd docker
docker-compose up
```

### Manual Build

```bash
docker build -t asa -f docker/Dockerfile .
docker run -p 8000:8000 asa
```

---

## Project Structure

```
asa/
├── src/asa/                # Main package
│   ├── core/               # Data models, evidence, utilities
│   ├── config/             # Settings and configuration
│   ├── ingestion/          # Repository cloning & ingestion
│   ├── analysis/           # Static analysis engine
│   │   ├── parsers/        # Tree-sitter parsers
│   │   └── extractors/     # Dependency graph builder
│   ├── knowledge_graph/    # Knowledge graph schema & queries
│   ├── agents/             # Autonomous analysis agents
│   ├── evidence/           # Evidence collection & verification
│   ├── security/           # Sandboxing and validation
│   ├── api/                # REST API (FastAPI)
│   ├── cli/                # Command-line interface (Typer)
│   ├── runtime/            # Runtime analysis
│   └── config/             # App configuration
├── frontend/               # React web interface
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── synthetic_repos/    # Synthetic test edge cases
├── benchmarks/             # Performance benchmarks
├── docker/                 # Docker configuration
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

---

## Development

### Setup

```bash
git clone https://github.com/gautamkr0104/asa.git
cd asa
pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=asa tests/

# Specific test file
pytest tests/unit/test_evidence.py -v
```

### Linting & Type Checking

```bash
# Lint
ruff check src/asa/

# Format
ruff format src/asa/

# Type check
mypy src/asa/
```

### Run Benchmarks

```bash
python benchmarks/scripts/run_benchmarks.py
```

### Code Standards

- Type hints on every function and method
- Follow existing code style (enforced by Ruff)
- Write tests for every new feature
- Update documentation for user-facing changes
- Atomic, well-described commits

---

## Roadmap

- [ ] LLM-powered codebase Q&A with RAG
- [ ] CI/CD pipeline integration (GitHub Actions analysis)
- [ ] Plugin system for custom analysis agents
- [ ] Webhook support for push-based analysis
- [ ] Dashboard with cross-repository analytics
- [ ] VS Code extension for in-editor analysis
- [ ] Support for additional data stores (Elasticsearch, ClickHouse)

---

## Limitations

- Dynamic imports may not be fully resolved
- Generated code is detected heuristically
- Runtime analysis is limited to safe execution scenarios
- LLM-powered reasoning requires API key configuration
- Very large repositories may hit memory limits

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## Author

**Gautam Kumar** — [@gautamkr0104](https://github.com/gautamkr0104)

---

## Credits

The visual design and branding of ASA were created by **Pihu**.

Follow her work on Instagram: [@jusst._.pihu](https://www.instagram.com/jusst._.pihu/)

---

<p align="center">
  <em>Built with evidence, not assumptions.</em>
</p>
