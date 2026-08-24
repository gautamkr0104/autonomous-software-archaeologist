"""Integration tests for the analysis pipeline."""

import asyncio
import os
import pytest
from asa.analysis.static.engine import StaticAnalysisEngine
from asa.ingestion.repository import RepositoryIngester


class TestIngestionAndAnalysis:
    """Test the ingestion + static analysis pipeline on a real local repo."""

    @pytest.fixture
    def sample_repo(self, tmp_path):
        """Create a minimal sample repository for testing."""
        repo = tmp_path / "sample-repo"
        repo.mkdir()

        # Create a .git directory
        (repo / ".git").mkdir()

        # Create source files
        (repo / "main.py").write_text('''
import os
from typing import Optional

class Application:
    """Main application class."""
    
    def __init__(self, name: str, debug: bool = False):
        self.name = name
        self.debug = debug
        self.db_url = os.environ.get("DATABASE_URL", "sqlite:///default.db")
    
    def run(self) -> None:
        print(f"Running {self.name}")
        self._setup_database()
    
    def _setup_database(self) -> None:
        print(f"Connecting to {self.db_url}")


def create_app() -> Application:
    app = Application(name="myapp", debug=True)
    app.run()
    return app


if __name__ == "__main__":
    create_app()
''')

        (repo / "utils.py").write_text('''
import hashlib
from typing import List


def compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def filter_items(items: List[str], predicate: callable) -> List[str]:
    return [item for item in items if predicate(item)]
''')

        (repo / "config.py").write_text('''
import os

class Config:
    DEBUG = os.environ.get("DEBUG", "false") == "true"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-prod")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    API_KEY = os.environ.get("API_KEY")
    
    @classmethod
    def is_production(cls) -> bool:
        return not cls.DEBUG
''')

        (repo / "tests").mkdir()
        (repo / "tests" / "__init__.py").write_text("")
        (repo / "tests" / "test_main.py").write_text('''
from main import Application, create_app


def test_application_creation():
    app = Application("test")
    assert app.name == "test"


def test_application_debug():
    app = Application("test", debug=True)
    assert app.debug is True
''')

        # Package files
        (repo / "requirements.txt").write_text('''
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
''')

        return repo

    def test_ingestion(self, sample_repo):
        ingester = RepositoryIngester()
        info, path = ingester.ingest(local_path=str(sample_repo))

        assert info.name == "sample-repo"
        assert "python" in info.languages
        assert info.total_files > 0

    def test_static_analysis(self, sample_repo):
        ingester = RepositoryIngester()
        info, path = ingester.ingest(local_path=str(sample_repo))

        engine = StaticAnalysisEngine()
        project = engine.analyze(info)

        assert project is not None
        assert len(project.file_analyses) > 0
        assert len(project.external_dependencies) > 0
        assert len(project.modules) > 0

        # Check that we found the class
        all_classes = [c for fa in project.file_analyses for c in fa.classes]
        class_names = [c.name for c in all_classes]
        assert "Application" in class_names
        assert "Config" in class_names

        # Check that we found functions
        all_functions = [f for fa in project.file_analyses for f in fa.functions]
        func_names = [f.name for f in all_functions]
        assert "compute_hash" in func_names or "create_app" in func_names

        # Check external dependencies
        dep_names = [d.name for d in project.external_dependencies]
        assert "fastapi" in dep_names or "uvicorn" in dep_names

        # Check environment variables
        all_envs = [ev for fa in project.file_analyses for ev in fa.environment_variables]
        assert "DATABASE_URL" in all_envs
        assert "DEBUG" in all_envs or "SECRET_KEY" in all_envs

    def test_dependency_graph(self, sample_repo):
        ingester = RepositoryIngester()
        info, path = ingester.ingest(local_path=str(sample_repo))

        engine = StaticAnalysisEngine()
        project = engine.analyze(info)

        graph = project.dependency_graph
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_test_file_detection(self, sample_repo):
        ingester = RepositoryIngester()
        info, path = ingester.ingest(local_path=str(sample_repo))

        engine = StaticAnalysisEngine()
        project = engine.analyze(info)

        test_files = [fa for fa in project.file_analyses if fa.is_test]
        assert len(test_files) > 0
        assert any("test_main" in f.file_path for f in test_files)
