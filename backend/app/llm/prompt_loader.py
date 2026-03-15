"""
dotprompt-style .prompt file loader.

File format:
    ---
    model: groq/llama-3.3-70b-versatile
    temperature: 0.4
    response_format: json_object
    ---
    Jinja2 template body...

The YAML frontmatter is optional. The body is rendered as a Jinja2 template.
Plugins register their own prompt directories; later-registered dirs take priority.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)


def _parse_prompt_file(text: str) -> tuple[dict, str]:
    """Split a .prompt file into (meta_dict, body_string)."""
    m = _FRONTMATTER_RE.match(text)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        body = text[m.end():]
    else:
        meta = {}
        body = text
    return meta, body.strip()


class PromptRegistry:
    """
    Registry of .prompt file directories.

    Supports multiple directories; later-registered dirs override earlier ones.
    Use the module-level ``registry`` singleton in application code.
    """

    def __init__(self) -> None:
        self._dirs: list[Path] = []
        self._env: Environment | None = None

    def register_dir(self, directory: Path) -> None:
        """Add a directory of .prompt files. Later registrations take priority."""
        if directory.exists():
            self._dirs.append(directory)
        self._env = None  # invalidate cached env

    def _get_env(self) -> Environment:
        if self._env is None:
            # Reversed so Jinja2 FileSystemLoader (first-match) honours later priority
            dirs = [str(d) for d in reversed(self._dirs) if d.exists()]
            self._env = Environment(
                loader=FileSystemLoader(dirs) if dirs else FileSystemLoader("/"),
                autoescape=False,
                keep_trailing_newline=True,
            )
        return self._env

    def _find_file(self, name: str) -> Path | None:
        """Return the highest-priority .prompt file for this name."""
        for directory in reversed(self._dirs):
            candidate = directory / f"{name}.prompt"
            if candidate.exists():
                return candidate
        return None

    def render(self, name: str, **variables: Any) -> tuple[dict, str]:
        """
        Load, render, and return (meta, body) for the named prompt.

        Raises FileNotFoundError if no matching .prompt file is found.
        """
        path = self._find_file(name)
        if path is None:
            searched = [str(d) for d in self._dirs]
            raise FileNotFoundError(
                f"Prompt {name!r} not found. Searched: {searched}"
            )

        raw = path.read_text(encoding="utf-8")
        meta, body_template = _parse_prompt_file(raw)

        env = self._get_env()
        rendered = env.from_string(body_template).render(**variables)
        return meta, rendered

    def render_body(self, name: str, **variables: Any) -> str:
        """Convenience: render and return only the body string."""
        _, body = self.render(name, **variables)
        return body


# Module-level singleton — import and use this everywhere
registry = PromptRegistry()
