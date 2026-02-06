"""Jujutsu command execution utilities."""

import json
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


class JujutsuCommandError(Exception):
    """Exception raised when a jj command fails."""

    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"jj command failed: {command} (exit code {returncode})\n{stderr}")


def run_jj_command(
    args: list[str],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
) -> tuple[str, str]:
    """
    Run a jj command and return stdout and stderr.

    Args:
        args: Command arguments (without 'jj' prefix)
        cwd: Working directory (defaults to current directory)
        capture_output: Whether to capture output

    Returns:
        Tuple of (stdout, stderr)

    Raises:
        JujutsuCommandError: If the command fails
    """
    cmd = ["jj", *args]
    logger.debug(f"Running command: {' '.join(cmd)}")

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
    args = ["log", "--template", "json"]
    if limit:
        args.extend(["-r", f"limit({limit}, all())"])

    stdout, _ = run_jj_command(args)
    log_entries = []

    # Parse JSON lines
    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry_data = json.loads(line)
            log_entries.append(
                LogEntry(
                    commit_id=entry_data.get("commit_id", ""),
                    description=entry_data.get("description"),
                    author=entry_data.get("author", {}).get("name") if entry_data.get("author") else None,
                    timestamp=entry_data.get("timestamp"),
                    parents=entry_data.get("parents", []),
                )
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse log entry: {line[:100]}... Error: {e}")

    # Get current revision
    current_stdout, _ = run_jj_command(["log", "-r", "@", "--template", "{commit_id}"])
    current_revision = current_stdout.strip()

    return RevisionGraph(revisions=log_entries, current_revision=current_revision)


def describe_revision(revision_id: str) -> RevisionInfo:
    """
    Get detailed information about a specific revision.

    Args:
        revision_id: The revision ID to describe

    Returns:
        RevisionInfo with revision details
    """
    # Get basic info
    stdout, _ = run_jj_command(["describe", revision_id])
    description = stdout.strip() if stdout.strip() else None

    # Get log entry for this revision
    stdout, _ = run_jj_command(["log", "-r", revision_id, "--template", "json", "-n", "1"])
    log_data = {}
    if stdout.strip():
        try:
            log_data = json.loads(stdout.strip())
        except json.JSONDecodeError:
            pass

    # Check for conflicts
    has_conflicts = False
    try:
        conflict_stdout, _ = run_jj_command(["diff", "-r", revision_id, "--conflicts"])
        has_conflicts = bool(conflict_stdout.strip())
    except JujutsuCommandError:
        # If command fails, assume no conflicts
        pass

    return RevisionInfo(
        revision_id=revision_id,
        description=description or log_data.get("description"),
        author=log_data.get("author", {}).get("name") if log_data.get("author") else None,
        timestamp=log_data.get("timestamp"),
        parents=log_data.get("parents", []),
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
    # Get last operation info
    stdout, _ = run_jj_command(["op", "log", "--template", "json", "-n", "1"])
    op_data = {}
    if stdout.strip():
        try:
            op_data = json.loads(stdout.strip())
        except json.JSONDecodeError:
            pass

    # Undo the operation
    run_jj_command(["op", "undo"])

    return OperationInfo(
        operation_id=op_data.get("operation_id", "unknown"),
        operation_type=op_data.get("operation_type", "unknown"),
        timestamp=op_data.get("timestamp"),
        description=op_data.get("description"),
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
        args.extend(["-p", parent])

    stdout, _ = run_jj_command(args)
    # Extract revision ID from output
    stdout, _ = run_jj_command(["log", "-r", "@", "--template", "{commit_id}"])
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
    stdout, _ = run_jj_command(["log", "-r", "@", "--template", "{commit_id}"])
    current_revision = stdout.strip()

    # Check for uncommitted changes
    stdout, _ = run_jj_command(["status"])
    has_uncommitted_changes = bool(stdout.strip())

    # Check for conflicts
    conflicts = []
    try:
        stdout, _ = run_jj_command(["diff", "--conflicts"])
        if stdout.strip():
            # Parse conflict output (simplified - actual parsing would be more complex)
            for line in stdout.strip().split("\n"):
                if "conflict" in line.lower() or ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        conflicts.append(
                            ConflictInfo(
                                file_path=parts[0].strip(),
                                conflict_type="merge",
                                details=parts[1].strip() if len(parts) > 1 else None,
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
    stdout, _ = run_jj_command(["diff", "-r", revset, "--conflicts"])

    conflicts = []
    if stdout.strip():
        # Parse conflict output
        for line in stdout.strip().split("\n"):
            if "conflict" in line.lower() or ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    conflicts.append(
                        ConflictInfo(
                            file_path=parts[0].strip(),
                            conflict_type="merge",
                            details=parts[1].strip() if len(parts) > 1 else None,
                        )
                    )

    return conflicts
