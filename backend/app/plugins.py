"""
osmosis plugin system.

Plugins are discovered via Python entry points (PEP 517/660).
Declare in your plugin's pyproject.toml:

    [project.entry-points."osmosis.plugins"]
    my_plugin = "my_package.plugin:MyPlugin"

Then `pip install` the package — osmosis picks it up on next startup.
No osmosis source code changes required.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import User

log = logging.getLogger(__name__)

_registry: list["OsmosisPlugin"] = []


@runtime_checkable
class OsmosisPlugin(Protocol):
    """
    Interface every osmosis plugin must implement.

    Only `name` is strictly required. All other methods have default
    no-op implementations so you only override what you need.
    """

    name: str       # unique slug, e.g. "word-of-day"
    version: str    # semver string, e.g. "0.1.0"

    def get_tools(self) -> list[dict]:
        """
        Return OpenAI function-calling tool definitions.
        These are merged into the LLM tool list for every conversation.
        """
        return []

    def get_tool_handlers(self) -> dict[str, "PluginHandler"]:
        """
        Return {tool_name: async_handler} for each tool you declared.

        Handler signature:
            async def handler(user: User, db: AsyncSession, **kwargs) -> dict
        """
        return {}

    def get_router(self) -> "APIRouter | None":
        """
        Return an optional FastAPI router.
        Mounted at /api/plugins/{plugin.name}
        """
        return None

    def get_media_types(self) -> list[str]:
        """
        Return media types this plugin can handle for goal creation.
        e.g. ["series", "movie", "book"]
        """
        return []

    def get_goal_actions(self) -> list[dict]:
        """
        Return goal-type actions this plugin provides.

        Each dict has:
            media_types: list[str]  — e.g. ["series", "movie"]
            id:          str        — unique action slug
            label:       str        — button label shown in UI
        """
        return []

    async def on_startup(self, app: "FastAPI") -> None:
        """Called once during app lifespan startup."""


# Type alias for plugin tool handlers
PluginHandler = "async callable (user, db, **kwargs) -> dict"


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

def load_plugins() -> list[OsmosisPlugin]:
    """
    Discover and instantiate all installed osmosis plugins via entry points.
    Call once on startup — results are cached in _registry.
    """
    from importlib.metadata import entry_points

    global _registry
    _registry = []

    eps = entry_points(group="osmosis.plugins")
    for ep in eps:
        try:
            cls = ep.load()
            plugin = cls()
            _registry.append(plugin)
            log.info("osmosis plugin loaded: %s v%s", plugin.name, getattr(plugin, "version", "?"))
        except Exception as exc:
            log.error("Failed to load plugin %r: %s", ep.name, exc)

    if not _registry:
        log.debug("No osmosis plugins installed.")

    return _registry


def get_plugins() -> list[OsmosisPlugin]:
    return list(_registry)


def all_tools(base_tools: list[dict]) -> list[dict]:
    """Merge base tool definitions with all plugin tools."""
    extras = [tool for plugin in _registry for tool in plugin.get_tools()]
    return base_tools + extras


def all_handlers() -> dict[str, object]:
    """Collect all plugin tool handlers keyed by tool name."""
    return {
        name: handler
        for plugin in _registry
        for name, handler in plugin.get_tool_handlers().items()
    }


def goal_actions_for(media_type: str) -> list[dict]:
    """Return all plugin-declared goal actions matching this media_type."""
    actions = []
    for plugin in _registry:
        for action in plugin.get_goal_actions():
            if media_type in action.get("media_types", []):
                actions.append({"id": action["id"], "label": action["label"]})
    return actions


def goal_media_types() -> list[str]:
    """Return unique media types across all plugins."""
    types: set[str] = set()
    for plugin in _registry:
        types.update(plugin.get_media_types())
    return sorted(types)
