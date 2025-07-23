"""Google Workspace MCP Server Package."""

from .config import logger
from .workspace import workspace

__version__ = "1.0.0"
__all__ = ["workspace", "logger"]
