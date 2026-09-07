"""NetworkFlow integration for Task upload communication."""

import networkx as nx
from typing import Optional

from edge_sim_py import NetworkFlow

from models import Task, TaskStatus


class TaskNetworkFlow:
    """Manages NetworkFlow creation for Task upload to EdgeServer.

    This class creates and manages a NetworkFlow to transfer Task input data
    from a User to an EdgeServer using EdgeSimPy's network infrastructure.
    """

    def __init__(self, task: Task, simulator):
        """Initialize TaskNetworkFlow with Task and Simulator.

        Args:
            task: Task to be uploaded (must have user, target_server, data_size_mb)
            simulator: EdgeSimPy Simulator instance

        Raises:
            ValueError: If task lacks required attributes
        """
        self.task = task
        self.simulator = simulator
        self.flow: Optional[NetworkFlow] = None

        # Validate task attributes
        if task.user is None:
            raise ValueError("Task must have a user")
        if task.target_server is None:
            raise ValueError("Task must have a target_server")
        if task.data_size_mb < 0:
            raise ValueError("Task must have non-negative data_size_mb")

    def create_upload_flow(self) -> NetworkFlow:
        """Create and register a NetworkFlow for Task upload.

        Returns:
            NetworkFlow: The created network flow

        Raises:
            ValueError: If network path cannot be calculated
        """
        # Identify network endpoints
        source_switch = self.task.user.base_station.network_switch
        target_server = self.task.target_server
        target_switch = target_server.base_station.network_switch

        if source_switch is None:
            raise ValueError("User must have a base_station with network_switch")
        if target_switch is None:
            raise ValueError("Target server must have a base_station with network_switch")

        # Calculate network path
        try:
            path = nx.shortest_path(
                G=self.simulator.topology,
                source=source_switch,
                target=target_switch,
                weight="delay",
                method="dijkstra",
            )
        except nx.NetworkXNoPath:
            raise ValueError(f"No network path between {source_switch} and {target_switch}")

        # Convert data size (MB to KB - operational hypothesis for EdgeSimPy)
        data_to_transfer = self.task.data_size_mb * 1024

        # Create NetworkFlow following EdgeSimPy pattern
        # source=NetworkSwitch (entry point), target=EdgeServer (logical destination)
        self.flow = NetworkFlow(
            topology=self.simulator.topology,
            source=source_switch,
            target=target_server,
            start=self.simulator.schedule.steps + 1,
            path=path,
            data_to_transfer=data_to_transfer,
                metadata={
                    "type": "task_input",
                    "task_id": self.task.task_id,
                    "object": self.task,
                },
        )

        # Register flow with simulator
        self.simulator.initialize_agent(agent=self.flow)

        # Update task state for transmission
        self.task.status = TaskStatus.TRANSMITTING
        self.task.transmission_start_time_s = (
            self.flow.start * self.simulator.tick_duration
        )

        return self.flow

    def update_transmission_metrics(self) -> None:
        """Update Task transmission metrics when flow completes.

        This should be called after the simulation step where the flow finishes.
        """
        if self.flow is None:
            raise ValueError("Flow not created")

        if self.flow.status != "finished":
            return  # Not yet complete

        # Calculate transmission times using EdgeSimPy clock
        self.task.transmission_end_time_s = (
            self.flow.end * self.simulator.tick_duration
        )
        # transmission_time_s is calculated automatically by property

    def get_flow_info(self) -> dict:
        """Get information about the current flow.

        Returns:
            dict: Flow information including status, data transfer, and timing
        """
        if self.flow is None:
            return {"status": "not_created"}

        return {
            "flow_id": self.flow.id,
            "status": self.flow.status,
            "data_to_transfer": self.flow.data_to_transfer,
            "bandwidth": self.flow.bandwidth,
            "start": self.flow.start,
            "end": self.flow.end,
            "path": [switch.id for switch in self.flow.path],
            "source": self.flow.source.id if self.flow.source else None,
            "target": self.flow.target.id if self.flow.target else None,
        }
