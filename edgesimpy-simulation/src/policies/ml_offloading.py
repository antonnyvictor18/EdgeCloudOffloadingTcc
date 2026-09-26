"""MLP-based offloading policy for Edge/Cloud decision."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.dataset import FEATURE_NAMES
from ml.mlp_model import MLPModel, MLPConfig
from ml.preprocessing import MinMaxNormalizer, NormalizationParams


class CloudUnavailableStatus(Enum):
    """Explicit status for Cloud prediction when Cloud is not implemented."""

    CLOUD_UNAVAILABLE = "CLOUD_UNAVAILABLE"


@dataclass(frozen=True)
class OffloadingDecision:
    """Result of MLP offloading decision."""

    predicted_destination: str  # "Edge" or "Cloud"
    execution_status: str  # "PENDING", "CLOUD_UNAVAILABLE", "FAILED"
    selected_edge_server: Optional[Any] = None
    features_used: Optional[Dict[str, float]] = None


@dataclass(frozen=True)
class MLPOffloadingConfig:
    """Configuration for MLP offloading policy."""

    model_path: Optional[Path] = None
    preprocessing_path: Optional[Path] = None
    feature_names: tuple[str, ...] = FEATURE_NAMES


class MLPOffloadingPolicy:
    """MLP-based offloading policy that predicts Edge vs Cloud.

    This policy:
    1. Loads a pre-trained MLP model and preprocessing parameters
    2. Extracts 6 features from a Task at decision time
    3. Applies the same preprocessing used during training
    4. Predicts Edge or Cloud
    5. Returns the prediction for further handling

    The policy does NOT:
    - Execute the task
    - Create NetworkFlow
    - Manipulate TaskScheduler
    - Select specific EdgeServer (use NearestServerPolicy for that)
    - Advance the simulation clock

    Feature extraction uses GLOBAL features (not destination-specific):
    - NetworkLatencyMs: average path delay to all candidate EdgeServers
    - BandwidthMbps: minimum bandwidth bottleneck to all candidate EdgeServers

    This matches the C# dataset semantics where these are single values per sample.
    """

    def __init__(self, config: MLPOffloadingConfig):
        """Initialize MLP offloading policy with pre-trained model.

        Args:
            config: Configuration containing model and preprocessing paths
        """
        self.config = config
        self.model: Optional[MLPModel] = None
        self._is_loaded = False

    def load_model(self) -> None:
        """Load pre-trained MLP model and preprocessing parameters.

        This method must be called before predict().

        If a model path is provided, load from disk. Otherwise, initialize
        a new model for training.
        """
        # Initialize model with fixed config (matching MLP_final_6)
        mlp_config = MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11)
        self.model = MLPModel(mlp_config)

        # Load from disk if path provided
        if self.config.model_path and self.config.model_path.with_suffix(".npz").exists():
            self.model.load(self.config.model_path)
            # The normalizer is loaded with the model
            self.normalizer = self.model._normalizer
        else:
            # Normalizer will be fitted during training
            self.normalizer = MinMaxNormalizer()

        self._is_loaded = True

    def fit_model(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """Fit the model on training data (for TCC integration reproducibility).

        Args:
            X_train: Training features
            y_train: Training labels
        """
        if not self._is_loaded:
            raise ValueError("Model must be loaded before fitting")

        # The model's fit method handles normalization internally
        # Train the model on raw data
        self.model.fit(X_train, y_train)

    def predict(self, task: Any, topology: Any) -> OffloadingDecision:
        """Predict Edge or Cloud for a given task.

        Args:
            task: Task object with required attributes
            topology: EdgeSimPy topology for network metrics

        Returns:
            OffloadingDecision with prediction and execution status

        Raises:
            ValueError: If model not loaded or task lacks required features
        """
        if not self._is_loaded:
            raise ValueError("Model must be loaded before prediction")

        if not self.model._is_fitted:
            raise ValueError("Model must be fitted before prediction")

        # Extract features in the exact order used during training
        features, features_dict = self._extract_features(task, topology)

        # Apply preprocessing (using fitted normalizer from model)
        features_array = np.array([features])
        features_normalized = self.model.normalizer.transform(features_array)

        # Predict
        prediction = self.model.predict(features_normalized)[0]

        # Determine execution status
        if prediction == "Cloud":
            execution_status = CloudUnavailableStatus.CLOUD_UNAVAILABLE.value
            selected_edge_server = None
        else:
            execution_status = "PENDING"
            selected_edge_server = None  # Will be selected by NearestServerPolicy

        return OffloadingDecision(
            predicted_destination=prediction,
            execution_status=execution_status,
            selected_edge_server=selected_edge_server,
            features_used=features_dict,
        )

    def _extract_features(self, task: Any, topology: Any) -> Tuple[Tuple[float, ...], Dict[str, float]]:
        """Extract 6 features from task in the exact training order.

        Order must match FEATURE_NAMES:
        1. CpuCycles
        2. TaskSizeMB
        3. LatencySensitivity
        4. RequiredMemoryMB
        5. BandwidthMbps
        6. NetworkLatencyMs

        Args:
            task: Task object
            topology: EdgeSimPy topology

        Returns:
            Tuple of (feature values, feature dict)
        """
        # Direct task attributes
        cpu_cycles = task.cpu_cycles
        task_size_mb = task.data_size_mb
        latency_sensitivity = task.latency_sensitivity
        required_memory_mb = task.required_memory_mb

        # Network-related features (need topology)
        bandwidth_mbps = self._get_bandwidth(task, topology)
        network_latency_ms = self._get_network_latency(task, topology)

        features = (
            cpu_cycles,
            task_size_mb,
            latency_sensitivity,
            required_memory_mb,
            bandwidth_mbps,
            network_latency_ms,
        )

        features_dict = {
            "CpuCycles": cpu_cycles,
            "TaskSizeMB": task_size_mb,
            "LatencySensitivity": latency_sensitivity,
            "RequiredMemoryMB": required_memory_mb,
            "BandwidthMbps": bandwidth_mbps,
            "NetworkLatencyMs": network_latency_ms,
        }

        return features, features_dict

    def _get_bandwidth(self, task: Any, topology: Any) -> float:
        """Get bandwidth as a GLOBAL feature.

        Formula:
        BandwidthMbps = minimum bandwidth bottleneck among all candidate EdgeServers

        This matches the C# dataset semantics where BandwidthMbps is a single
        value per sample, not per-destination.

        Args:
            task: Task with user
            topology: EdgeSimPy topology

        Returns:
            Bandwidth in Mbps

        Raises:
            ValueError: If no network context or no EdgeServers available
        """
        if task.user is None or task.user.base_station is None:
            raise ValueError("Task must have a user with base_station")

        user_switch = task.user.base_station.network_switch
        if user_switch is None:
            raise ValueError("User must have a network_switch")

        # Get all edge servers and calculate bandwidth to each
        from edge_sim_py import EdgeServer

        edge_servers = list(EdgeServer.all())
        if not edge_servers:
            raise ValueError("No EdgeServers available")

        # Calculate minimum bandwidth bottleneck to all edge servers
        bandwidths = []
        for server in edge_servers:
            server_switch = server.base_station.network_switch
            if server_switch is None:
                continue

            try:
                import networkx as nx
                path = nx.shortest_path(
                    G=topology,
                    source=user_switch,
                    target=server_switch,
                    weight="delay",
                    method="dijkstra",
                )

                # Find minimum bandwidth along path (bottleneck)
                path_bandwidths = []
                for i in range(len(path) - 1):
                    link = topology[path[i]][path[i + 1]]
                    if link and hasattr(link, "bandwidth"):
                        path_bandwidths.append(link.bandwidth)

                if path_bandwidths:
                    bandwidths.append(min(path_bandwidths))
            except Exception as e:
                # If path calculation fails, skip this server
                print(f"Warning: Could not calculate bandwidth to server {server.id}: {e}")
                continue

        if not bandwidths:
            raise ValueError("Could not calculate bandwidth to any EdgeServer")

        # Return minimum bottleneck among all candidates
        return min(bandwidths)

    def _get_network_latency(self, task: Any, topology: Any) -> float:
        """Get network latency as a GLOBAL feature.

        Formula:
        NetworkLatencyMs = average path delay to all candidate EdgeServers

        This matches the C# dataset semantics where NetworkLatencyMs is a
        single value per sample, not per-destination.

        Args:
            task: Task with user
            topology: EdgeSimPy topology

        Returns:
            Network latency in milliseconds

        Raises:
            ValueError: If no network context or no EdgeServers available
        """
        if task.user is None or task.user.base_station is None:
            raise ValueError("Task must have a user with base_station")

        user_switch = task.user.base_station.network_switch
        if user_switch is None:
            raise ValueError("User must have a network_switch")

        # Get all edge servers and calculate latency to each
        from edge_sim_py import EdgeServer

        edge_servers = list(EdgeServer.all())
        if not edge_servers:
            raise ValueError("No EdgeServers available")

        # Calculate average path delay to all edge servers
        path_delays = []
        for server in edge_servers:
            server_switch = server.base_station.network_switch
            if server_switch is None:
                continue

            try:
                import networkx as nx
                path = nx.shortest_path(
                    G=topology,
                    source=user_switch,
                    target=server_switch,
                    weight="delay",
                    method="dijkstra",
                )
                # Calculate path delay manually from link delays
                total_delay = 0.0
                for i in range(len(path) - 1):
                    link = topology[path[i]][path[i + 1]]
                    if link and hasattr(link, "delay"):
                        total_delay += link.delay
                path_delays.append(total_delay)
            except Exception:
                # If path calculation fails, skip this server
                continue

        if not path_delays:
            raise ValueError("Could not calculate network latency to any EdgeServer")

        # Return average path delay among all candidates
        return sum(path_delays) / len(path_delays)


def create_mlp_offloading_policy(
    model_path: Optional[Path] = None,
    preprocessing_path: Optional[Path] = None,
) -> MLPOffloadingPolicy:
    """Factory function to create MLP offloading policy.

    Args:
        model_path: Path to saved model weights (optional for TCC integration)
        preprocessing_path: Path to saved preprocessing parameters

    Returns:
        Configured MLPOffloadingPolicy instance
    """
    config = MLPOffloadingConfig(
        model_path=model_path,
        preprocessing_path=preprocessing_path,
    )
    return MLPOffloadingPolicy(config)
