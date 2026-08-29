"""Minimal construction check for the independent Task domain model."""

from models import Task, TaskStatus


def main() -> None:
    task = Task(task_id="smoke-1")

    assert task.status is TaskStatus.CREATED
    assert task.creation_time_s == 0.0
    assert task.selected_server is None
    assert task.completion_time_s is None
    assert task.deadline_violation is None

    print(f"Task criada: id={task.task_id}, status={task.status.value}")
    print(
        "Estado inicial: "
        f"creation_time_s={task.creation_time_s}, "
        f"selected_server={task.selected_server}, "
        f"completion_time_s={task.completion_time_s}"
    )


if __name__ == "__main__":
    main()