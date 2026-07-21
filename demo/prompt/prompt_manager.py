"""
Jinja2-based prompt manager — mirrors the pattern used in scopic-agent-studio.

Usage:
    manager = PromptManager()
    system = manager.render("sentiment_system.j2", language="Vietnamese")
    user   = manager.render("sentiment_user.j2", language="Vietnamese", text="Sản phẩm rất tốt!")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptManager:
    _instance: PromptManager | None = None

    def __new__(cls) -> PromptManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_env()
        return cls._instance

    def _init_env(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            trim_blocks=True,       # strip newline after {% ... %} blocks
            lstrip_blocks=True,     # strip leading whitespace before {% ... %}
            keep_trailing_newline=True,
            autoescape=False,       # prompts are plain text, not HTML
        )
        self._env.filters["count"] = len  # {{ items | count }}

    def render(self, template_name: str, **kwargs: Any) -> str:
        try:
            tpl = self._env.get_template(template_name)
        except TemplateNotFound:
            available = [t for t in _TEMPLATES_DIR.glob("**/*.j2")]
            raise FileNotFoundError(
                f"Template '{template_name}' not found. "
                f"Available: {[p.name for p in available]}"
            )
        return tpl.render(**kwargs)
