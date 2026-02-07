"""MCP server for Jujutsu version control."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from . import jj_commands
from .models import RevisionGraph, RevisionInfo, StatusInfo, ConflictInfo, OperationInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Jujutsu MCP Server")


def _setup_workspace_path(ctx: Optional[Context] = None) -> None:
    """
    Setup workspace path from context or environment variables.
    
    Args:
        ctx: Optional MCP context (if available)
    """
    # Try to get workspace path from context metadata if available
    if ctx:
        # Try multiple ways to extract workspace path from context
        workspace_paths_to_try = []
        
        # Method 1: Check request_context.meta attributes
        if hasattr(ctx, 'request_context') and ctx.request_context:
            if hasattr(ctx.request_context, 'meta') and ctx.request_context.meta:
                meta = ctx.request_context.meta
                # Check common metadata fields that might contain workspace path
                for attr in ['workspace_path', 'workspacePath', 'workspace', 'cwd', 'root']:
                    if hasattr(meta, attr):
                        path_value = getattr(meta, attr)
                        if path_value:
                            workspace_paths_to_try.append(str(path_value))
        
        # Method 2: Check context attributes directly
        for attr in ['workspace_path', 'workspacePath', 'workspace', 'cwd', 'root']:
            if hasattr(ctx, attr):
                path_value = getattr(ctx, attr)
                if path_value:
                    workspace_paths_to_try.append(str(path_value))
        
        # Method 3: Try to get from context dict-like access if available
        if hasattr(ctx, '__dict__'):
            for key, value in ctx.__dict__.items():
                if 'workspace' in key.lower() or 'cwd' in key.lower() or 'root' in key.lower():
                    if isinstance(value, (str, Path)):
                        workspace_paths_to_try.append(str(value))
        
        # Try each potential workspace path
        for path_str in workspace_paths_to_try:
            try:
                workspace_path = Path(path_str).resolve()
                # Try jj root from this path
                try:
                    stdout, _ = subprocess.run(
                        ["jj", "root"],
                        cwd=workspace_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    repo_root = Path(stdout.strip()).resolve()
                    if repo_root.exists():
                        jj_commands.set_workspace_path(repo_root)
                        logger.debug(f"Set workspace path from context: {repo_root}")
                        return
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # If jj root fails, check if path itself contains .jj
                    if (workspace_path / ".jj").exists():
                        jj_commands.set_workspace_path(workspace_path)
                        logger.debug(f"Set workspace path from context: {workspace_path}")
                        return
            except Exception as e:
                logger.debug(f"Error parsing workspace path from context: {e}")
                continue
    
    # Let find_jj_repo_root handle the detection (includes environment variables, jj root, and recursive search)
    repo_root = jj_commands.find_jj_repo_root()
    if repo_root:
        jj_commands.set_workspace_path(repo_root)
        logger.debug(f"Set workspace path from detection: {repo_root}")
    else:
        logger.warning(
            "Could not detect jj repository root. "
            "MCP tools may fail with 'There is no jj repo in \".\"' error. "
            "Consider setting CURSOR_WORKSPACE_PATH or WORKSPACE_PATH environment variable in MCP server configuration."
        )


@mcp.tool()
async def get_log(limit: Optional[int] = None, ctx: Context = CurrentContext()) -> dict:
    """
    Get the revision log as a structured graph.

    Args:
        limit: Maximum number of revisions to return (optional)

    Returns:
        Dictionary containing revision graph with revisions and current revision
    """
    try:
        _setup_workspace_path(ctx)
        graph = jj_commands.get_log(limit=limit)
        return graph.model_dump()
    except Exception as e:
        logger.error(f"Error in get_log: {e}", exc_info=True)
        raise


@mcp.tool()
async def describe_revision(revision_id: str, ctx: Context = CurrentContext()) -> dict:
    """
    Get detailed information about a specific revision.

    Args:
        revision_id: The revision ID to describe (can be a revset like '@', '@-', etc.)

    Returns:
        Dictionary containing revision information including description, author, parents, and conflict status
    """
    try:
        _setup_workspace_path(ctx)
        info = jj_commands.describe_revision(revision_id)
        return info.model_dump()
    except Exception as e:
        logger.error(f"Error in describe_revision: {e}", exc_info=True)
        raise


@mcp.tool()
async def smart_rebase(source: str, destination: str, ctx: Context = CurrentContext()) -> str:
    """
    Perform a rebase operation using revsets.

    Args:
        source: Source revision (revset, e.g., '@', '@-', 'main')
        destination: Destination revision (revset)

    Returns:
        Success message
    """
    try:
        _setup_workspace_path(ctx)
        return jj_commands.smart_rebase(source, destination)
    except Exception as e:
        logger.error(f"Error in smart_rebase: {e}", exc_info=True)
        raise


@mcp.tool()
async def undo_last_op(ctx: Context = CurrentContext()) -> dict:
    """
    Undo the last operation safely.

    Returns:
        Dictionary containing information about the undone operation
    """
    try:
        _setup_workspace_path(ctx)
        op_info = jj_commands.undo_last_op()
        return op_info.model_dump()
    except Exception as e:
        logger.error(f"Error in undo_last_op: {e}", exc_info=True)
        raise


@mcp.tool()
async def new_change(parent: Optional[str] = None, ctx: Context = CurrentContext()) -> str:
    """
    Create a new change (equivalent to 'jj new').

    Args:
        parent: Optional parent revision (revset). If not specified, uses the current working copy.

    Returns:
        New revision ID
    """
    try:
        _setup_workspace_path(ctx)
        return jj_commands.new_change(parent=parent)
    except Exception as e:
        logger.error(f"Error in new_change: {e}", exc_info=True)
        raise


@mcp.tool()
async def squash_changes(revision: str, into: str, ctx: Context = CurrentContext()) -> str:
    """
    Squash changes from one revision into another.

    Args:
        revision: Revision to squash (revset)
        into: Target revision (revset)

    Returns:
        Success message
    """
    try:
        _setup_workspace_path(ctx)
        return jj_commands.squash_changes(revision, into)
    except Exception as e:
        logger.error(f"Error in squash_changes: {e}", exc_info=True)
        raise


@mcp.tool()
async def get_status(ctx: Context = CurrentContext()) -> dict:
    """
    Get the current repository status.

    Returns:
        Dictionary containing current revision, uncommitted changes status, and conflicts
    """
    try:
        _setup_workspace_path(ctx)
        status = jj_commands.get_status()
        return status.model_dump()
    except Exception as e:
        logger.error(f"Error in get_status: {e}", exc_info=True)
        raise


@mcp.tool()
async def resolve_conflicts(revision: Optional[str] = None, ctx: Context = CurrentContext()) -> list[dict]:
    """
    Detect and analyze conflicts in a revision.

    Args:
        revision: Optional revision to check (revset, defaults to current '@')

    Returns:
        List of conflict information dictionaries
    """
    try:
        _setup_workspace_path(ctx)
        conflicts = jj_commands.resolve_conflicts(revision=revision)
        return [c.model_dump() for c in conflicts]
    except Exception as e:
        logger.error(f"Error in resolve_conflicts: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    mcp.run()
