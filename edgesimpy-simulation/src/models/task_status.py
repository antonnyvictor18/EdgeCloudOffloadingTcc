"""Statuses used by the future temporal task lifecycle."""

from enum import Enum


class TaskStatus(str, Enum):
    """Lifecycle states for a computational task."""

    CREATED = "created"
    QUEUED = "queued"
    TRANSMITTING = "transmitting"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"