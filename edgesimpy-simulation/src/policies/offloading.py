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
