"""Enumerations and type aliases used throughout ASA."""

from __future__ import annotations

from enum import Enum, auto


class AnalysisPhase(str, Enum):
    """Phases of the analysis pipeline."""

    INGESTION = "ingestion"
    STATIC_ANALYSIS = "static_analysis"
    DEPENDENCY_GRAPH = "dependency_graph"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    ARCHITECTURE_INFERENCE = "architecture_inference"
    GIT_HISTORY = "git_history"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    VERIFICATION = "verification"
    RUNTIME = "runtime"


class AgentStatus(str, Enum):
    """Lifecycle status of an analysis agent."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class NodeType(str, Enum):
    """Entity types in the knowledge graph."""

    REPOSITORY = "Repository"
    COMMIT = "Commit"
    FILE = "File"
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    API = "API"
    DATABASE = "Database"
    EXTERNAL_SERVICE = "ExternalService"
    CONFIGURATION = "Configuration"
    TEST = "Test"
    AGENT_FINDING = "AgentFinding"
    ARCHITECTURAL_COMPONENT = "ArchitecturalComponent"
    INTERFACE = "Interface"
    VARIABLE = "Variable"
    IMPORT = "Import"
    EXPORT = "Export"
    MESSAGE_QUEUE = "MessageQueue"
    ENVIRONMENT_VARIABLE = "EnvironmentVariable"


class RelationshipType(str, Enum):
    """Edge types in the knowledge graph."""

    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    EXPOSES = "EXPOSES"
    CONSUMES = "CONSUMES"
    PUBLISHES = "PUBLISHES"
    READS_FROM = "READS_FROM"
    WRITES_TO = "WRITES_TO"
    CONFIGURED_BY = "CONFIGURED_BY"
    TESTED_BY = "TESTED_BY"
    CHANGED_IN = "CHANGED_IN"
    DEPENDS_ON = "DEPENDS_ON"
    EVIDENCED_BY = "EVIDENCED_BY"
    USES = "USES"
    EXTENDS = "EXTENDS"
    DECORATES = "DECORATES"
    RETURNS = "RETURNS"
    THROWS = "THROWS"


class EvidenceType(str, Enum):
    """Categories of evidence backing a claim."""

    AST_NODE = "ast_node"
    IMPORT_STATEMENT = "import_statement"
    FUNCTION_CALL = "function_call"
    CONFIGURATION_VALUE = "configuration_value"
    FILE_PATH = "file_path"
    GIT_COMMIT = "git_commit"
    GIT_BLAME = "git_blame"
    DEPENDENCY_DECLARATION = "dependency_declaration"
    HTTP_ENDPOINT = "http_endpoint"
    DATABASE_QUERY = "database_query"
    ENVIRONMENT_VARIABLE = "environment_variable"
    TEST_COVERAGE = "test_coverage"
    RUNTIME_TRACE = "runtime_trace"
    STATIC_ANALYSIS = "static_analysis"
    MANUAL_REVIEW = "manual_review"
    LLM_REASONING = "llm_reasoning"


class FindingSeverity(str, Enum):
    """Severity of an architectural finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Category of an architectural finding."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    DEPENDENCY = "dependency"
    COMPLEXITY = "complexity"
    CODE_QUALITY = "code_quality"
