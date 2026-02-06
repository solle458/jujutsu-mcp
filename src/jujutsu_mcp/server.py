"""MCP server for Jujutsu version control."""

import logging
from typing import Optional

from fastmcp import FastMCP

from . import jj_commands
from .models import RevisionGraph, RevisionInfo, StatusInfo, ConflictInfo, OperationInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Jujutsu MCP Server")


@mcp.tool()
def get_log(limit: Optional[int] = None) -> dict:
    """
    Get the revision log as a structured graph.

    Args:
        limit: Maximum number of revisions to return (optional)

    Returns:
        Dictionary containing revision graph with revisions and current revision
    """
    try:
        graph = jj_commands.get_log(limit=limit)
        return graph.model_dump()
    except Exception as e:
        logger.error(f"Error in get_log: {e}", exc_info=True)
        raise


@mcp.tool()
def describe_revision(revision_id: str) -> dict:
    """
    Get detailed information about a specific revision.

    Args:
        revision_id: The revision ID to describe (can be a revset like '@', '@-', etc.)

    Returns:
        Dictionary containing revision information including description, author, parents, and conflict status
    """
    try:
        info = jj_commands.describe_revision(revision_id)
        return info.model_dump()
    except Exception as e:
        logger.error(f"Error in describe_revision: {e}", exc_info=True)
        raise


@mcp.tool()
def smart_rebase(source: str, destination: str) -> str:
    """
    Perform a rebase operation using revsets.

    Args:
        source: Source revision (revset, e.g., '@', '@-', 'main')
        destination: Destination revision (revset)

    Returns:
        Success message
    """
    try:
        return jj_commands.smart_rebase(source, destination)
    except Exception as e:
        logger.error(f"Error in smart_rebase: {e}", exc_info=True)
        raise


@mcp.tool()
def undo_last_op() -> dict:
    """
    Undo the last operation safely.

    Returns:
        Dictionary containing information about the undone operation
    """
    try:
        op_info = jj_commands.undo_last_op()
        return op_info.model_dump()
    except Exception as e:
        logger.error(f"Error in undo_last_op: {e}", exc_info=True)
        raise


@mcp.tool()
def new_change(parent: Optional[str] = None) -> str:
    """
    Create a new change (equivalent to 'jj new').

    Args:
        parent: Optional parent revision (revset). If not specified, uses the current working copy.

    Returns:
        New revision ID
    """
    try:
        return jj_commands.new_change(parent=parent)
    except Exception as e:
        logger.error(f"Error in new_change: {e}", exc_info=True)
        raise


@mcp.tool()
def squash_changes(revision: str, into: str) -> str:
    """
    Squash changes from one revision into another.

    Args:
        revision: Revision to squash (revset)
        into: Target revision (revset)

    Returns:
        Success message
    """
    try:
        return jj_commands.squash_changes(revision, into)
    except Exception as e:
        logger.error(f"Error in squash_changes: {e}", exc_info=True)
        raise


@mcp.tool()
def get_status() -> dict:
    """
    Get the current repository status.

    Returns:
        Dictionary containing current revision, uncommitted changes status, and conflicts
    """
    try:
        status = jj_commands.get_status()
        return status.model_dump()
    except Exception as e:
        logger.error(f"Error in get_status: {e}", exc_info=True)
        raise


@mcp.tool()
def resolve_conflicts(revision: Optional[str] = None) -> list[dict]:
    """
    Detect and analyze conflicts in a revision.

    Args:
        revision: Optional revision to check (revset, defaults to current '@')

    Returns:
        List of conflict information dictionaries
    """
    try:
        conflicts = jj_commands.resolve_conflicts(revision=revision)
        return [c.model_dump() for c in conflicts]
    except Exception as e:
        logger.error(f"Error in resolve_conflicts: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    mcp.run()
