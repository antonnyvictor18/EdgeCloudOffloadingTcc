"""Domain models that are independent from the EdgeSimPy runtime."""

from .task import Task
from .task_status import TaskStatus

__all__ = ["Task", "TaskStatus"]