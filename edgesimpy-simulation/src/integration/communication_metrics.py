"""Communication metrics that keep native and derived values separate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class CommunicationMetrics:
    """Metrics for one Task upload.

    ``transmission_time_s`` is observed from the Task/NetworkFlow timeline.
    ``path_delay_dataset_units`` is the sum of NetworkLink ``delay`` values.
    The current dataset does not declare the delay unit in its JSON schema, so
    a seconds conversion is intentionally not performed.
    """

    task_id: int | str
    user_id: int | str
    target_server_id: int | str
    path: tuple[int, ...]
    hops: int
    path_delay_dataset_units: float
    transmission_time_s: Optional[float]
    derived_communication_latency_s: Optional[float]
    is_local: bool

    @classmethod
    def from_task(
        cls,
        task: Any,
        server: Any,
        topology: Any,
        path: Sequence[Any],
    ) -> "CommunicationMetrics":
        """Build metrics from an executed Task and its selected path."""
        path_nodes = tuple(node.id for node in path)
        path_delay = float(topology.calculate_path_delay(path=list(path)))
        transmission_time = task.transmission_time_s

        if transmission_time is not None and transmission_time < 0:
            raise ValueError("transmission time cannot be negative")
        if path_delay < 0:
            raise ValueError("path delay cannot be negative")

        user_switch = task.user.base_station.network_switch
        server_switch = server.base_station.network_switch
        return cls(
            task_id=task.task_id,
            user_id=task.user.id,
            target_server_id=server.id,
            path=path_nodes,
            hops=len(path_nodes) - 1,
            path_delay_dataset_units=path_delay,
            transmission_time_s=transmission_time,
            derived_communication_latency_s=None,
            is_local=user_switch == server_switch,
        )
