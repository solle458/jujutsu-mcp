"""Data models for Jujutsu MCP Server."""

from typing import Optional
from pydantic import BaseModel, Field


class RevisionInfo(BaseModel):
    """Information about a revision."""

    revision_id: str = Field(..., description="The revision ID")
    description: Optional[str] = Field(None, description="Commit message/description")
    author: Optional[str] = Field(None, description="Author name")
    timestamp: Optional[str] = Field(None, description="Commit timestamp")
    parents: list[str] = Field(default_factory=list, description="Parent revision IDs")
    has_conflicts: bool = Field(default=False, description="Whether this revision has conflicts")


class LogEntry(BaseModel):
    """A single log entry from jj log."""

    commit_id: str = Field(..., description="Commit ID")
    description: Optional[str] = Field(None, description="Commit description")
    author: Optional[str] = Field(None, description="Author")
    timestamp: Optional[str] = Field(None, description="Timestamp")
    parents: list[str] = Field(default_factory=list, description="Parent commit IDs")


class RevisionGraph(BaseModel):
    """Graph structure of revisions."""

    revisions: list[LogEntry] = Field(default_factory=list, description="List of revisions")
    current_revision: Optional[str] = Field(None, description="Current working copy revision")


class ConflictInfo(BaseModel):
    """Information about conflicts."""

    file_path: str = Field(..., description="Path to the conflicted file")
    conflict_type: str = Field(..., description="Type of conflict")
    details: Optional[str] = Field(None, description="Additional conflict details")


class OperationInfo(BaseModel):
    """Information about a jj operation."""

    operation_id: str = Field(..., description="Operation ID")
    operation_type: str = Field(..., description="Type of operation")
    timestamp: Optional[str] = Field(None, description="Operation timestamp")
    description: Optional[str] = Field(None, description="Operation description")


class StatusInfo(BaseModel):
    """Current repository status."""

    current_revision: str = Field(..., description="Current revision ID")
    has_uncommitted_changes: bool = Field(default=False, description="Whether there are uncommitted changes")
    conflicts: list[ConflictInfo] = Field(default_factory=list, description="List of conflicts if any")
