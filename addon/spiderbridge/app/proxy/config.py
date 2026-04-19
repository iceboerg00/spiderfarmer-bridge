from pathlib import Path
import yaml


def load_config(path: str = "config/config.yaml") -> dict:
    """Load YAML config file. Raises FileNotFoundError if missing."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(p) as f:
        return yaml.safe_load(f)
