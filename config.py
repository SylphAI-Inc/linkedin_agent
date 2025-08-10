import os
import socket
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False


def load_env() -> bool:
    """Load environment variables from the project root .env file if present.

    Returns True if a .env file was found and loaded; otherwise False.
    """
    try:
        root = Path(__file__).resolve().parent
        dotenv_path = root / ".env"
        if dotenv_path.exists():
            return bool(load_dotenv(dotenv_path))
        # Fallback: attempt default resolution
        return bool(load_dotenv())
    except Exception:
        return False


@dataclass
class ModelConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))


@dataclass
class AgentConfig:
    max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "20"))


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        except Exception:
            return False


def _pick_cdp_port() -> int:
    # Respect explicit env if set
    env_port = os.getenv("CHROME_CDP_PORT")
    if env_port and env_port.isdigit():
        try:
            return int(env_port)
        except Exception:
            pass
    # Find a free port in a small range
    for p in range(9222, 9233):
        if not _is_port_in_use(p):
            return p
    # Fallback
    return 9233


@dataclass
class CDPConfig:
    port: int = field(default_factory=_pick_cdp_port)
    headless: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"
    user_data_dir: str = os.getenv("USER_DATA_DIR", "./chrome_data")
    
    def ensure_chrome_running(self):
        """Ensure Chrome CDP is running"""
        import subprocess
        import time
        import requests
        
        try:
            # Test if CDP is already running
            requests.get(f"http://localhost:{self.port}/json/version", timeout=2)
            return True
        except:
            # Start Chrome with CDP
            subprocess.Popen([
                "chromium-browser",
                "--headless",
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir=./chrome_data-{self.port}",
                "--no-first-run",
                "--no-default-browser-check", 
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--remote-allow-origins=*",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for startup
            for _ in range(10):
                try:
                    requests.get(f"http://localhost:{self.port}/json/version", timeout=2)
                    time.sleep(1)  # Extra wait for stability
                    return True
                except:
                    time.sleep(1)
            return False


def get_model_kwargs(provider: Optional[str] = None):
    provider = (provider or ModelConfig().provider).lower()
    if provider == "openai":
        return {"model": ModelConfig().model, "temperature": ModelConfig().temperature}
    # Extend for other providers if needed
    return {"temperature": ModelConfig().temperature}

def get(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)
