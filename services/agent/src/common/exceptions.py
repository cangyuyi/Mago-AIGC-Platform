"""Custom exceptions."""


class AgentError(Exception):
    """Base exception for agent errors."""

    def __init__(self, message: str, code: str = "agent_error", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class LLMError(AgentError):
    """LLM call failed."""

    def __init__(self, message: str, model: str = "", details: dict | None = None):
        super().__init__(message, code="llm_error", details={"model": model, **(details or {})})


class WorkflowError(AgentError):
    """Workflow execution error."""

    def __init__(self, message: str, node: str = "", details: dict | None = None):
        super().__init__(message, code="workflow_error", details={"node": node, **(details or {})})


class KnowledgeBaseError(AgentError):
    """Knowledge base error."""

    pass


class ValidationError(AgentError):
    """Input validation error."""

    def __init__(self, message: str, field: str = ""):
        super().__init__(message, code="validation_error", details={"field": field})
