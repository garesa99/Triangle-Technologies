"""Node config loader. Supports YAML (if PyYAML present) or JSON. See config.example.yaml."""
from __future__ import annotations

import json
import os
from typing import Any


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        text = f.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            raise SystemExit("PyYAML not installed — use a .json config or `pip install pyyaml`")
    return json.loads(text)


def env_override(cfg: dict[str, Any]) -> dict[str, Any]:
    """Env vars override the file: TRIANGLE_NODE_ID, TRIANGLE_BRAIN_URL, TRIANGLE_TOKEN."""
    if os.environ.get("TRIANGLE_NODE_ID"):
        cfg["node_id"] = os.environ["TRIANGLE_NODE_ID"]
    if os.environ.get("TRIANGLE_BRAIN_URL"):
        cfg["brain_url"] = os.environ["TRIANGLE_BRAIN_URL"]
    if os.environ.get("TRIANGLE_TOKEN"):
        cfg["token"] = os.environ["TRIANGLE_TOKEN"]
    return cfg
