"""
Configuration for Recursive://Neon backend
"""
from pydantic_settings import BaseSettings
from pathlib import Path


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

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    models_dir: Path = base_dir / "services" / "ollama" / "models"
    data_dir: Path = base_dir / "game_data"
    game_data_path: Path = base_dir / "game_data"  # Alias for data_dir
    chromadb_dir: Path = base_dir / "data" / "chromadb"

    # Game Configuration
    max_npcs: int = 20
    npc_memory_context_length: int = 10  # Last N messages to remember
    max_response_tokens: int = 200

    # Performance
    ollama_timeout: int = 60  # seconds
    websocket_timeout: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
