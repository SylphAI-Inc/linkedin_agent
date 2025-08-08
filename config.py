import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    def load_dotenv(*args, **kwargs):
        return False


# Load .env at import time
load_dotenv()


@dataclass
class ModelConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))


@dataclass
class AgentConfig:
    max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "20"))


@dataclass
class CDPConfig:
    port: int = int(os.getenv("CHROME_CDP_PORT", "9222"))
    headless: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"
    user_data_dir: str = os.getenv("USER_DATA_DIR", "./chrome_data")


def get_model_kwargs(provider: Optional[str] = None):
    provider = (provider or ModelConfig().provider).lower()
    if provider == "openai":
        return {"model": ModelConfig().model, "temperature": ModelConfig().temperature}
    # Extend for other providers if needed
    return {"temperature": ModelConfig().temperature}
import os
from pathlib import Path
from dotenv import load_dotenv


def load_env():
    # Load from project root .env
    root = Path(__file__).resolve().parent
    dotenv_path = root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
    else:
        # Fallback: load from CWD if running elsewhere
        load_dotenv()


def get(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)
