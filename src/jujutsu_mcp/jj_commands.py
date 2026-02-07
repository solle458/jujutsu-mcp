"""Jujutsu command execution utilities."""

import json
import os
import subprocess
import logging
from typing import Optional
from pathlib import Path

from .models import (
    RevisionInfo,
    LogEntry,
    RevisionGraph,
    ConflictInfo,
    StatusInfo,
    OperationInfo,
)

logger = logging.getLogger(__name__)

# Global cache for workspace path (per session)
_workspace_path_cache: Optional[Path] = None


class JujutsuCommandError(Exception):
    """Exception raised when a jj command fails."""

    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"jj command failed: {command} (exit code {returncode})\n{stderr}")


def find_jj_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the root directory of a jj repository.
    
    Tries multiple methods in order:
    1. Use cached workspace path if available
    2. Check environment variables (CURSOR_WORKSPACE_PATH, WORKSPACE_PATH, PWD)
    3. Use jj root command from start_path or current directory
    
    Args:
        start_path: Optional starting path for jj root search
        
    Returns:
        Path to jj repository root, or None if not found
    """
    global _workspace_path_cache
    
    # Use cached path if available
    if _workspace_path_cache is not None and _workspace_path_cache.exists():
        return _workspace_path_cache
    
    # Try environment variables
    env_vars = ["CURSOR_WORKSPACE_PATH", "WORKSPACE_PATH", "PWD"]
    for env_var in env_vars:
        env_path = os.environ.get(env_var)
        if env_path:
            try:
                path = Path(env_path).resolve()
                # Check if this path or a parent contains .jj directory
                if (path / ".jj").exists():
                    _workspace_path_cache = path
                    logger.debug(f"Found jj repo root from {env_var}: {path}")
                    return path
                # Try jj root from this path
                try:
                    stdout, _ = subprocess.run(
                        ["jj", "root"],
                        cwd=path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    repo_root = Path(stdout.strip()).resolve()
                    if repo_root.exists():
                        _workspace_path_cache = repo_root
                        logger.debug(f"Found jj repo root via jj root from {env_var}: {repo_root}")
                        return repo_root
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            except Exception as e:
                logger.debug(f"Error checking {env_var}: {e}")
                continue
    
    # Try jj root command from start_path or current directory
    search_path = start_path if start_path else Path.cwd()
    try:
        stdout, _ = subprocess.run(
            ["jj", "root"],
            cwd=search_path,
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = Path(stdout.strip()).resolve()
        if repo_root.exists():
            _workspace_path_cache = repo_root
            logger.debug(f"Found jj repo root via jj root from {search_path}: {repo_root}")
            return repo_root
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.debug(f"jj root command failed from {search_path}: {e}")
    
    return None


def set_workspace_path(path: Optional[Path]) -> None:
    """
    Set the workspace path explicitly (useful for MCP context).
    
    Args:
        path: Path to the workspace root, or None to clear cache
    """
    global _workspace_path_cache
    _workspace_path_cache = path
    if path:
        logger.debug(f"Workspace path set to: {path}")
    else:
        logger.debug("Workspace path cache cleared")


def run_jj_command(
    args: list[str],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
) -> tuple[str, str]:
    """
    Run a jj command and return stdout and stderr.

    Args:
        args: Command arguments (without 'jj' prefix)
        cwd: Working directory (defaults to detected workspace path or current directory)
        capture_output: Whether to capture output

    Returns:
        Tuple of (stdout, stderr)

    Raises:
        JujutsuCommandError: If the command fails
    """
    # If cwd is not specified, try to find jj repo root
    if cwd is None:
        repo_root = find_jj_repo_root()
        if repo_root:
            cwd = repo_root
            logger.debug(f"Using detected workspace path: {cwd}")
        else:
            # Fallback to current directory
            cwd = Path.cwd()
            logger.debug(f"No workspace path detected, using current directory: {cwd}")
    
    cmd = ["jj", *args]
    logger.debug(f"Running command: {' '.join(cmd)} in {cwd}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise JujutsuCommandError(
                command=" ".join(cmd),
                returncode=result.returncode,
                stderr=result.stderr,
            )

        return result.stdout, result.stderr
    except FileNotFoundError:
        raise RuntimeError("jj command not found. Please ensure Jujutsu is installed.")


def get_log(limit: Optional[int] = None) -> RevisionGraph:
    """
    Get the revision log as a structured graph.

    Args:
        limit: Maximum number of revisions to return

    Returns:
        RevisionGraph with parsed log entries
    """
    # Get list of revision IDs first
    revset = f"limit({limit}, all())" if limit else "all()"
    args = ["log", "-r", revset, "--template", "commit_id", "-G"]
    stdout, _ = run_jj_command(args)
    
    # Extract commit IDs from output (one per line when using -G)
    commit_ids = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line and len(line) >= 8:  # Valid commit ID
            commit_ids.append(line)
    
    log_entries = []
    
    # For each commit, get individual fields
    for commit_id in commit_ids:
        try:
            # Get description
            desc_stdout, _ = run_jj_command(["log", "-r", commit_id, "--template", "description.first_line()", "-n", "1", "-G"])
            description = desc_stdout.strip() if desc_stdout.strip() else None
            
            # Get author
            author_stdout, _ = run_jj_command(["log", "-r", commit_id, "--template", "author.name()", "-n", "1", "-G"])
            author = author_stdout.strip() if author_stdout.strip() else None
            
            # Get timestamp - skip for now as format_timestamp syntax is complex
            # Can be added later if needed
            timestamp = None
            
            # Get parents - use log to get parent commit IDs
            parents = []
            try:
                # Get parent revisions using revset syntax
                parent_stdout, _ = run_jj_command(["log", "-r", f"{commit_id}-", "--template", "commit_id", "-G"])
                for line in parent_stdout.strip().split("\n"):
                    line = line.strip()
                    if line and len(line) >= 8:
                        parents.append(line)
            except JujutsuCommandError:
                pass
            
            log_entries.append(
                LogEntry(
                    commit_id=commit_id,
                    description=description if description else None,
                    author=author if author else None,
                    timestamp=timestamp if timestamp else None,
                    parents=parents,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to get log entry for {commit_id}: {e}")
            continue

    # Get current revision
    current_stdout, _ = run_jj_command(["log", "-r", "@", "--template", "commit_id", "-n", "1", "-G"])
    current_revision = current_stdout.strip() if current_stdout.strip() else None

    return RevisionGraph(revisions=log_entries, current_revision=current_revision)


def describe_revision(revision_id: str) -> RevisionInfo:
    """
    Get detailed information about a specific revision.

    Args:
        revision_id: The revision ID to describe

    Returns:
        RevisionInfo with revision details
    """
    # Get description
    desc_stdout, _ = run_jj_command(["log", "-r", revision_id, "--template", "description.first_line()", "-n", "1", "-G"])
    description = desc_stdout.strip() if desc_stdout.strip() else None

    # Get author name
    author_stdout, _ = run_jj_command(["log", "-r", revision_id, "--template", "author.name()", "-n", "1", "-G"])
    author = author_stdout.strip() if author_stdout.strip() else None

    # Get timestamp - skip for now as format_timestamp syntax is complex
    timestamp = None

    # Get parents
    parents = []
    try:
        parent_stdout, _ = run_jj_command(["log", "-r", f"{revision_id}-", "--template", "commit_id", "-G"])
        for line in parent_stdout.strip().split("\n"):
            line = line.strip()
            if line and len(line) >= 8:
                parents.append(line)
    except JujutsuCommandError:
        pass

    # Check for conflicts using jj resolve --list
    has_conflicts = False
    try:
        conflict_stdout, _ = run_jj_command(["resolve", "--list", "-r", revision_id])
        has_conflicts = bool(conflict_stdout.strip())
    except JujutsuCommandError:
        # If command fails, assume no conflicts
        pass

    return RevisionInfo(
        revision_id=revision_id,
        description=description,
        author=author,
        timestamp=timestamp,
        parents=parents,
        has_conflicts=has_conflicts,
    )


def smart_rebase(source: str, destination: str) -> str:
    """
    Perform a rebase operation.

    Args:
        source: Source revision (revset)
        destination: Destination revision (revset)

    Returns:
        Success message
    """
    stdout, _ = run_jj_command(["rebase", "-s", source, "-o", destination])
    return stdout.strip() or f"Rebased {source} onto {destination}"


def undo_last_op() -> OperationInfo:
    """
    Undo the last operation.

    Returns:
        Information about the undone operation
    """
    # Get last operation info - parse from op log output
    operation_id = "unknown"
    operation_type = "unknown"
    timestamp = None
    description = None
    
    try:
        # Get operation details from op log
        op_stdout, _ = run_jj_command(["op", "log", "-n", "1", "-G"])
        if op_stdout.strip():
            # Parse operation info from output format:
            # <operation_id> <user>@<host> <timestamp>, lasted <duration>
            # <operation_type>
            # args: <args>
            lines = op_stdout.strip().split("\n")
            if len(lines) > 0:
                # First line contains operation ID, user, timestamp
                first_line = lines[0].strip()
                parts = first_line.split()
                if len(parts) > 0:
                    operation_id = parts[0]
                # Extract timestamp if present
                for part in parts:
                    if "now" in part.lower() or "," in part:
                        timestamp = part.rstrip(",")
                        break
            if len(lines) > 1:
                # Second line is usually the operation type/description
                operation_type = lines[1].strip()
                description = operation_type
    except JujutsuCommandError:
        pass

    # Undo the operation
    run_jj_command(["op", "undo"])

    return OperationInfo(
        operation_id=operation_id,
        operation_type=operation_type,
        timestamp=timestamp,
        description=description,
    )


def new_change(parent: Optional[str] = None) -> str:
    """
    Create a new change.

    Args:
        parent: Optional parent revision (revset)

    Returns:
        New revision ID
    """
    args = ["new"]
    if parent:
        # jj new doesn't have -p option, parent is specified as an argument
        args.append(parent)

    stdout, _ = run_jj_command(args)
    # Extract revision ID from output
    stdout, _ = run_jj_command(["log", "-r", "@", "--template", "commit_id", "-n", "1", "-G"])
    return stdout.strip()


def squash_changes(revision: str, into: str) -> str:
    """
    Squash changes from one revision into another.

    Args:
        revision: Revision to squash (revset)
        into: Target revision (revset)

    Returns:
        Success message
    """
    stdout, _ = run_jj_command(["squash", "--from", revision, "--into", into])
    return stdout.strip() or f"Squashed {revision} into {into}"


def get_status() -> StatusInfo:
    """
    Get the current repository status.

    Returns:
        StatusInfo with current state
    """
    # Get current revision
    stdout, _ = run_jj_command(["log", "-r", "@", "--template", "commit_id", "-n", "1", "-G"])
    current_revision = stdout.strip()

    # Check for uncommitted changes using status --porcelain
    has_uncommitted_changes = False
    try:
        stdout, _ = run_jj_command(["status", "--porcelain"])
        # Porcelain format shows one line per changed file
        # If there's any output, there are uncommitted changes
        has_uncommitted_changes = bool(stdout.strip())
    except JujutsuCommandError:
        # Fallback to regular status
        try:
            stdout, _ = run_jj_command(["status"])
            # Check if there are working copy changes
            has_uncommitted_changes = "Working copy changes:" in stdout
        except JujutsuCommandError:
            pass

    # Check for conflicts using jj resolve --list
    conflicts = []
    try:
        stdout, _ = run_jj_command(["resolve", "--list"])
        if stdout.strip():
            # Parse conflict file paths from resolve --list output
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    conflicts.append(
                        ConflictInfo(
                            file_path=line,
                            conflict_type="merge",
                            details=None,
                        )
                    )
    except JujutsuCommandError:
        pass

    return StatusInfo(
        current_revision=current_revision,
        has_uncommitted_changes=has_uncommitted_changes,
        conflicts=conflicts,
    )


def resolve_conflicts(revision: Optional[str] = None) -> list[ConflictInfo]:
    """
    Detect and analyze conflicts.

    Args:
        revision: Optional revision to check (defaults to current)

    Returns:
        List of conflict information
    """
    revset = revision or "@"
    conflicts = []
    
    try:
        stdout, _ = run_jj_command(["resolve", "--list", "-r", revset])
        if stdout.strip():
            # Parse conflict file paths from resolve --list output
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    conflicts.append(
                        ConflictInfo(
                            file_path=line,
                            conflict_type="merge",
                            details=None,
                        )
                    )
    except JujutsuCommandError:
        # If command fails, assume no conflicts
        pass

    return conflicts
