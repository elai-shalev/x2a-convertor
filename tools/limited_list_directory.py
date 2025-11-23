"""Limited ListDirectoryTool that truncates large directory listings."""

from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_community.tools.file_management.list_dir import (
    ListDirectoryTool,
)
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Safety limits to prevent context overflow
MAX_LISTING_ITEMS = 50  # Maximum files/dirs to show
TRUNCATE_MESSAGE = (
    f"\n... (showing first {MAX_LISTING_ITEMS} items, "
    f"use list_directory on subdirectories)"
)


class LimitedListDirectoryInput(BaseModel):
    """Input schema for limited directory listing."""

    dir_path: str = Field(description="The path to the directory to list")


class LimitedListDirectoryTool(BaseTool):
    """List directory contents with limits to prevent context overflow.

    This tool wraps ListDirectoryTool but truncates listings that exceed
    MAX_LISTING_ITEMS to prevent filling up the context window.
    """

    name: str = "list_directory"
    description: str = (
        "List the contents of a directory. "
        f"Shows up to {MAX_LISTING_ITEMS} items. "
        "Use on subdirectories to see more files."
    )
    args_schema: dict[str, Any] | type[BaseModel] | None = (
        LimitedListDirectoryInput
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._list_tool = ListDirectoryTool()

    def _run(self, dir_path: str) -> str:
        """List directory with item limits.

        Args:
            dir_path: Path to the directory to list

        Returns:
            Directory listing (truncated if too many items) or error message
        """
        try:
            path = Path(dir_path)
            if not path.exists():
                return f"ERROR: Directory '{dir_path}' does not exist."

            if not path.is_dir():
                return f"ERROR: '{dir_path}' is not a directory."

            # Get the listing from the base tool
            listing = self._list_tool._run(dir_path)

            # Count items (lines that aren't empty or errors)
            lines = [
                line
                for line in listing.split("\n")
                if line.strip() and not line.startswith("ERROR")
            ]
            item_count = len(lines)

            # Truncate if necessary
            if item_count > MAX_LISTING_ITEMS:
                truncated_lines = lines[:MAX_LISTING_ITEMS]
                truncated = "\n".join(truncated_lines) + TRUNCATE_MESSAGE
                logger.info(
                    f"Truncated directory listing for {dir_path} from "
                    f"{item_count} to {MAX_LISTING_ITEMS} items"
                )
                return truncated

            return listing

        except Exception as e:
            error_msg = f"ERROR: Failed to list directory '{dir_path}': {e!s}"
            logger.error(error_msg)
            return error_msg
