# Technical Debt

Tracking deferred improvements and known issues.

## Unused LLM/AI Dependencies

- **Date**: 2026-03-26
- **Location**: `backend/pyproject.toml` lines 30-36
- **Summary**: `langchain-community`, `langgraph`, and `chromadb` are listed as core dependencies but appear unused. Only `langchain-core` (message types) and `langchain-ollama` (ChatOllama) are imported.
- **Why deferred**: Removing dependencies requires verifying no transitive import relies on them, and the project may use them in upcoming phases (e.g., RAG/memory features).
- **Suggested approach**: Run `pip-autoremove` or `pipdeptree` to confirm no transitive usage, then remove from `[project.dependencies]`. Add back individually when actually needed.
