"""Task offloading policies independent from simulation execution."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Sequence

import networkx as nx


class OffloadingPolicy(ABC):
    """Select an execution server without executing or scheduling a Task."""

    @abstractmethod
    def select_server(self, task: Any, candidates: Sequence[Any]) -> Any:
        """Return the selected server from the supplied candidates."""


class FixedServerPolicy(OffloadingPolicy):
    """Always select one explicitly configured server."""

    def __init__(self, server: Any):
        self.server = server

    def select_server(self, task: Any, candidates: Sequence[Any]) -> Any:
        if self.server not in candidates:
            raise ValueError("configured server is not a candidate")
        return self.server


class NearestServerPolicy(OffloadingPolicy):
    """Select the candidate with the smallest network path delay."""

    def __init__(self, topology: Any):
        self.topology = topology

    def select_server(self, task: Any, candidates: Sequence[Any]) -> Any:
        if task.user is None or task.user.base_station is None:
            raise ValueError("task user must have a base station")

        user_switch = task.user.base_station.network_switch
        if user_switch is None:
            raise ValueError("task user must have a network switch")
        if not candidates:
            raise ValueError("at least one candidate server is required")

        return min(
            candidates,
            key=lambda server: self._path_delay(user_switch, server),
        )

    def path_for(self, task: Any, server: Any) -> list[Any]:
        """Return the delay-weighted path used to compare a candidate."""
        user_switch = task.user.base_station.network_switch
        server_switch = server.base_station.network_switch
        return nx.shortest_path(
            G=self.topology,
            source=user_switch,
            target=server_switch,
            weight="delay",
            method="dijkstra",
        )

    def _path_delay(self, user_switch: Any, server: Any) -> float:
        server_switch = server.base_station.network_switch
        path = nx.shortest_path(
            G=self.topology,
            source=user_switch,
            target=server_switch,
            weight="delay",
            method="dijkstra",
        )
        return self.topology.calculate_path_delay(path)


class RandomPolicy(OffloadingPolicy):
    """Select a candidate using a dedicated seeded pseudo-random generator."""

    def __init__(self, seed: int):
        self.seed = seed
        self._random = random.Random(seed)

    def select_server(self, task: Any, candidates: Sequence[Any]) -> Any:
        if not candidates:
            raise ValueError("at least one candidate server is required")
        return self._random.choice(list(candidates))


class LeastLoadedPolicy(OffloadingPolicy):
    """Choose the candidate with the fewest admitted Tasks.

    EdgeSimPy has no native Task queue or execution-load metric. This policy
    therefore tracks only assignments already made by the TCC experiment.
    It does not inspect future completion, queue time, or deadline outcomes.
    """

    def __init__(self) -> None:
        self._admitted_task_count: dict[Any, int] = {}

    def select_server(self, task: Any, candidates: Sequence[Any]) -> Any:
        if not candidates:
            raise ValueError("at least one candidate server is required")
        return min(
            candidates,
            key=lambda server: (
                self._admitted_task_count.get(server, 0),
                server.id,
            ),
        )

    def record_assignment(self, server: Any) -> None:
        """Record a decision after the selected server is accepted."""
        self._admitted_task_count[server] = self._admitted_task_count.get(server, 0) + 1

    def admitted_task_count(self, server: Any) -> int:
        """Return the known admission count for a candidate server."""
        return self._admitted_task_count.get(server, 0)


class HybridHeuristicPolicy(OffloadingPolicy):
    """Balance path delay and prior Task admissions with fixed equal weights.

    Both signals are known before simulation starts. Delay is normalized among
    the current candidates; admission load is normalized using the current
    minimum and maximum counts. This is a static batch-decision heuristic, not
    a dynamic EdgeSimPy load controller.
    """

    def __init__(self, topology: Any, delay_weight: float = 0.5, load_weight: float = 0.5):
        if delay_weight < 0 or load_weight < 0 or delay_weight + load_weight == 0:
            raise ValueError("heuristic weights must be non-negative and not both zero")
        self.topology = topology
        self.delay_weight = delay_weight
        self.load_weight = load_weight
        self._admitted_task_count: dict[Any, int] = {}

    def select_server(self, task: Any, candidates: Sequence[Any]) -> Any:
        if not candidates:
            raise ValueError("at least one candidate server is required")

        scores = self.score_candidates(task, candidates)

        return min(
            candidates,
            key=lambda server: (
                scores[server]["cost"],
                server.id,
            ),
        )

    def score_candidates(self, task: Any, candidates: Sequence[Any]) -> dict[Any, dict[str, float]]:
        """Return normalized signals and cost for each current candidate."""
        if not candidates:
            raise ValueError("at least one candidate server is required")

        delays = {server: self._path_delay(task, server) for server in candidates}
        loads = {server: self._admitted_task_count.get(server, 0) for server in candidates}
        normalized_delays = self._normalize(delays)
        normalized_loads = self._normalize(loads)
        return {
            server: {
                "path_delay_ms": delays[server],
                "admitted_load": float(loads[server]),
                "delay_normalized": normalized_delays[server],
                "load_normalized": normalized_loads[server],
                "cost": (
                    self.delay_weight * normalized_delays[server]
                    + self.load_weight * normalized_loads[server]
                ),
            }
            for server in candidates
        }

    def record_assignment(self, server: Any) -> None:
        """Record an accepted decision for later decisions in the batch."""
        self._admitted_task_count[server] = self._admitted_task_count.get(server, 0) + 1

    def _path_delay(self, task: Any, server: Any) -> float:
        user_switch = task.user.base_station.network_switch
        server_switch = server.base_station.network_switch
        path = nx.shortest_path(
            G=self.topology,
            source=user_switch,
            target=server_switch,
            weight="delay",
            method="dijkstra",
        )
        return float(self.topology.calculate_path_delay(path))

    @staticmethod
    def _normalize(values: dict[Any, float]) -> dict[Any, float]:
        minimum = min(values.values())
        maximum = max(values.values())
        if maximum == minimum:
            return {key: 0.0 for key in values}
        return {
            key: (value - minimum) / (maximum - minimum)
            for key, value in values.items()
        }
