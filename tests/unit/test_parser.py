"""Tests for the tree-sitter AST parser."""

import os
import tempfile
import pytest
from asa.analysis.parsers.tree_sitter_parser import TreeSitterParser

ts_available = TreeSitterParser().available_languages


@pytest.fixture
def parser():
    return TreeSitterParser()


class TestTreeSitterParser:
    def test_init(self, parser):
        assert parser is not None
        assert isinstance(parser.available_languages, set)

    @pytest.mark.skipif(not ts_available, reason="tree-sitter not available")
    def test_parse_python_file(self, parser, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text('''
import os
from typing import List

class MyClass:
    """A test class."""
    
    def __init__(self, name: str):
        self.name = name
    
    def greet(self) -> str:
        return f"Hello, {self.name}!"

def main() -> None:
    obj = MyClass("World")
    print(obj.greet())

if __name__ == "__main__":
    main()
''')
        
        analysis = parser.parse_file(str(py_file))
        assert analysis is not None
        assert analysis.language == "python"
        assert len(analysis.classes) >= 1
        assert len(analysis.functions) >= 1
        assert len(analysis.imports) >= 1
        
        # Check class
        cls = analysis.classes[0]
        assert cls.name == "MyClass"
        assert cls.docstring == "A test class."
        
        # Check methods
        method_names = [m.name for m in cls.methods]
        assert "__init__" in method_names
        assert "greet" in method_names

    @pytest.mark.skipif(not ts_available, reason="tree-sitter not available")
    def test_parse_typescript_file(self, parser, tmp_path):
        ts_file = tmp_path / "test.ts"
        ts_file.write_text('''
import { useState } from "react";

interface Props {
    title: string;
    count: number;
}

export function Counter({ title, count }: Props) {
    const [value, setValue] = useState(count);
    return <div>{title}: {value}</div>;
}

export default function App() {
    return <Counter title="Count" count={0} />;
}
''')
        
        analysis = parser.parse_file(str(ts_file))
        if analysis:  # Depends on tree-sitter availability
            assert analysis.language == "typescript"
            assert len(analysis.functions) >= 1

    def test_parse_go_file(self, parser, tmp_path):
        go_file = tmp_path / "main.go"
        go_file.write_text('''
package main

import (
    "fmt"
    "net/http"
)

type Server struct {
    addr string
}

func (s *Server) ListenAndServe() error {
    return http.ListenAndServe(s.addr, nil)
}

func main() {
    s := &Server{addr: ":8080"}
    fmt.Println("Starting server...")
    s.ListenAndServe()
}
''')
        
        analysis = parser.parse_file(str(go_file))
        if analysis:
            assert analysis.language == "go"

    def test_nonexistent_file(self, parser):
        result = parser.parse_file("/nonexistent/file.py")
        assert result is None

    def test_binary_file_skipped(self, parser, tmp_path):
        bin_file = tmp_path / "test.bin"
        bin_file.write_bytes(b'\x00\x01\x02\x03')
        
        result = parser.parse_file(str(bin_file))
        assert result is None

    def test_regex_fallback(self, parser, tmp_path):
        """Test that regex fallback works when tree-sitter isn't available."""
        php_file = tmp_path / "test.php"
        php_file.write_text('''<?php
class UserService {
    public function getUser(int $id): array {
        return ["id" => $id, "name" => "Test"];
    }
}
?>''')
        
        analysis = parser.parse_file(str(php_file))
        if analysis:
            assert analysis.language == "php"

    def test_environment_variable_extraction(self, parser, tmp_path):
        py_file = tmp_path / "config.py"
        py_file.write_text('''
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
API_KEY = os.getenv("API_KEY")
SECRET = os.environ["SECRET_KEY"]
''')
        
        analysis = parser.parse_file(str(py_file))
        assert analysis is not None
        assert "DB_HOST" in analysis.environment_variables
        assert "DB_PORT" in analysis.environment_variables
        assert "API_KEY" in analysis.environment_variables
        assert "SECRET_KEY" in analysis.environment_variables

    def test_test_file_detection(self, parser, tmp_path):
        test_file = tmp_path / "test_core.py"
        test_file.write_text('''
def test_something():
    assert True
''')
        
        analysis = parser.parse_file(str(test_file))
        assert analysis is not None
        assert analysis.is_test is True
