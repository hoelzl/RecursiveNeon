"""
Configuration for Recursive://Neon backend
"""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory — resolved once at import time
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings"""

    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True

    # Ollama Configuration
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    ollama_binary_path: str = "../services/ollama"
    default_model: str = "qwen3:4b"  # Lightweight model for NPCs

    # Paths — base_dir is the backend/ directory.
    # Derived paths are recomputed from base_dir by _resolve_derived_paths
    # so that overriding base_dir via env var propagates correctly.
    base_dir: Path = _BACKEND_DIR
    models_dir: Path = _BACKEND_DIR / "services" / "ollama" / "models"
    data_dir: Path = _BACKEND_DIR / "game_data"
    chromadb_dir: Path = _BACKEND_DIR / "data" / "chromadb"
    initial_fs_path: Path = Path(__file__).resolve().parent / "initial_fs"

    # Game Configuration
    max_npcs: int = 20
    npc_max_conversation_history: int = 50  # Total messages stored on NPC model
    npc_memory_context_length: int = 10  # Last N messages fed to LLM window
    max_response_tokens: int = 200

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Performance
    ollama_timeout: int = 60  # seconds
    websocket_timeout: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def _resolve_derived_paths(self) -> "Settings":
        """Re-derive dependent paths from base_dir.

        Only overrides fields that were NOT explicitly set (via env var,
        .env file, or constructor kwargs).  Uses ``model_fields_set`` to
        distinguish explicit values from defaults.
        """
        bd = self.base_dir
        if "models_dir" not in self.model_fields_set:
            self.models_dir = bd / "services" / "ollama" / "models"
        if "data_dir" not in self.model_fields_set:
            self.data_dir = bd / "game_data"
        if "chromadb_dir" not in self.model_fields_set:
            self.chromadb_dir = bd / "data" / "chromadb"
        return self


settings = Settings()
