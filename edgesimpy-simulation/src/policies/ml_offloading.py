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
from ml.wisard_model import WISARD_CSHARP_EQUIVALENT, WISARD_FINAL_6, WiSARDConfig, WiSARDModel


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


def extract_task_features(task: Any, topology: Any) -> Tuple[Tuple[float, ...], Dict[str, float]]:
    """Extract the 6 contract features from a task in the exact training order.

    Shared by all ML offloading policies (MLP, WiSARD) so that the runtime
    feature vector is identical regardless of the model - single source of
    truth for the FEATURE_NAMES contract.

    Order must match FEATURE_NAMES:
    1. CpuCycles
    2. TaskSizeMB
    3. LatencySensitivity
    4. RequiredMemoryMB
    5. BandwidthMbps
    6. NetworkLatencyMs

    For the two network features, prefers the task's scenario WAN attributes
    (task.bandwidth_mbps / task.network_latency_ms), matching the C# contract
    where they are per-sample user->Cloud WAN conditions. If absent, falls
    back to topology-derived values over all EdgeServers - a documented
    semantic approximation, not the same variable.
    """
    cpu_cycles = task.cpu_cycles
    task_size_mb = task.data_size_mb
    latency_sensitivity = task.latency_sensitivity
    required_memory_mb = task.required_memory_mb
    bandwidth_mbps = _bandwidth_feature(task, topology)
    network_latency_ms = _network_latency_feature(task, topology)

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


def _bandwidth_feature(task: Any, topology: Any) -> float:
    """BandwidthMbps feature.

    C# contract: per-scenario WAN condition on the user->Cloud path
    (sampled LogUniform(2,1000)), used only in the Cloud cost term. It is
    NOT an edge-topology property. Runtime: prefer task.bandwidth_mbps;
    topology bottleneck (all EdgeServers) is a documented fallback.
    """
    if getattr(task, "bandwidth_mbps", None) is not None:
        return float(task.bandwidth_mbps)

    if task.user is None or task.user.base_station is None:
        raise ValueError("Task must have a user with base_station")

    user_switch = task.user.base_station.network_switch
    if user_switch is None:
        raise ValueError("User must have a network_switch")

    from edge_sim_py import EdgeServer

    edge_servers = list(EdgeServer.all())
    if not edge_servers:
        raise ValueError("No EdgeServers available")

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

            path_bandwidths = []
            for i in range(len(path) - 1):
                link = topology[path[i]][path[i + 1]]
                if link and hasattr(link, "bandwidth"):
                    path_bandwidths.append(link.bandwidth)

            if path_bandwidths:
                bandwidths.append(min(path_bandwidths))
        except Exception as e:
            print(f"Warning: Could not calculate bandwidth to server {server.id}: {e}")
            continue

    if not bandwidths:
        raise ValueError("Could not calculate bandwidth to any EdgeServer")

    return min(bandwidths)


def _network_latency_feature(task: Any, topology: Any) -> float:
    """NetworkLatencyMs feature.

    C# contract: per-scenario WAN latency on the user->Cloud path
    (sampled Uniform(2,180)), used only in the Cloud cost term. It is NOT
    an edge-topology property. Runtime: prefer task.network_latency_ms;
    topology average path delay (all EdgeServers) is a documented fallback.
    """
    if getattr(task, "network_latency_ms", None) is not None:
        return float(task.network_latency_ms)

    if task.user is None or task.user.base_station is None:
        raise ValueError("Task must have a user with base_station")

    user_switch = task.user.base_station.network_switch
    if user_switch is None:
        raise ValueError("User must have a network_switch")

    from edge_sim_py import EdgeServer

    edge_servers = list(EdgeServer.all())
    if not edge_servers:
        raise ValueError("No EdgeServers available")

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
            total_delay = 0.0
            for i in range(len(path) - 1):
                link = topology[path[i]][path[i + 1]]
                if link and hasattr(link, "delay"):
                    total_delay += link.delay
            path_delays.append(total_delay)
        except Exception:
            continue

    if not path_delays:
        raise ValueError("Could not calculate network latency to any EdgeServer")

    return sum(path_delays) / len(path_delays)


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

    Feature extraction order matches FEATURE_NAMES. For the two network
    features (BandwidthMbps, NetworkLatencyMs), the policy prefers the task's
    scenario WAN attributes (task.bandwidth_mbps / task.network_latency_ms),
    matching the C# contract where they are per-sample user->Cloud WAN
    conditions. If absent, it falls back to topology-derived values over all
    EdgeServers - a documented semantic approximation, not the same variable.
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

        # Pass RAW features to model.predict() - it handles normalization internally
        # This prevents double normalization bug discovered in parity audit
        features_array = np.array([features])
        prediction = self.model.predict(features_array)[0]

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

        Delegates to the shared extract_task_features() so that MLP and
        WiSARD policies produce identical feature vectors.
        """
        return extract_task_features(task, topology)


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


@dataclass(frozen=True)
class WiSARDOffloadingConfig:
    """Configuration for WiSARD offloading policy.

    `model` defaults to WISARD_FINAL_6 - the configuration frozen by
    experimento_tuning_wisard.py (validation-only selection, 5 mapping
    seeds). WISARD_CSHARP_EQUIVALENT reproduces the C# WisardStrategy
    hyperparameters and is kept as the reference baseline (it collapses to
    ~all-Edge on this contract because ties are resolved to Edge).

    The feature contract is the frozen 6-feature vector (FEATURE_NAMES) -
    NOT the 12-feature C# Features() vector, which includes server-state
    fields (EdgeCpuUsagePercent, EdgeQueueSize, CloudCpuUsagePercent,
    CloudQueueSize) that have no Task-level equivalent in the EdgeSimPy
    runtime. The encoder normalization is fitted on the training split
    rather than the C# fixed FeatureRanges. This policy is a WiSARD trained
    on the shared contract, not a bit-for-bit port of the C# strategy.
    """

    model: WiSARDConfig = WISARD_FINAL_6
    feature_names: tuple[str, ...] = FEATURE_NAMES


class WiSARDOffloadingPolicy:
    """WiSARD-based offloading policy that predicts Edge vs Cloud.

    Same decision contract as MLPOffloadingPolicy: extracts the 6 contract
    features from a Task at decision time and returns an OffloadingDecision
    (Cloud predictions are CLOUD_UNAVAILABLE, no fallback).

    There is no serialized WiSARD artifact; the model is trained in-session
    via fit_model() on the dataset's training split. Training is
    deterministic: the encoder is fitted on X_train and the RAM mapping is
    seeded by WiSARDConfig.seed.
    """

    def __init__(self, config: WiSARDOffloadingConfig):
        self.config = config
        self.model = WiSARDModel(config.model)
        self._is_fitted = False

    def fit_model(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """Train the WiSARD model on raw features (encoder fits internally).

        Args:
            X_train: Training features (raw, 6-feature contract order)
            y_train: Training labels ("Edge"/"Cloud")
        """
        self.model.fit(np.asarray(X_train, dtype=float), np.asarray(y_train))
        self._is_fitted = True

    def predict(self, task: Any, topology: Any) -> OffloadingDecision:
        """Predict Edge or Cloud for a given task.

        Passes RAW features to model.predict() - the WiSARD encoder handles
        normalization/quantization internally. Never pre-normalize (same
        class of bug as the MLP double-normalization).
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction")

        features, features_dict = extract_task_features(task, topology)
        prediction = self.model.predict(np.array([features]))[0]

        execution_status = (
            CloudUnavailableStatus.CLOUD_UNAVAILABLE.value
            if prediction == "Cloud"
            else "PENDING"
        )

        return OffloadingDecision(
            predicted_destination=prediction,
            execution_status=execution_status,
            selected_edge_server=None,
            features_used=features_dict,
        )

    def scores_for_task(self, task: Any, topology: Any) -> Dict[str, int]:
        """Discriminator scores for a task's feature vector.

        WiSARD has no continuous probability; the pre-argmax output is the
        per-class RAM hit counts. Used by parity tests to verify the policy
        path produces the exact same decision evidence as the model path.
        """
        features, _ = extract_task_features(task, topology)
        return self.scores(np.array([features]))

    def scores(self, X: np.ndarray) -> Dict[str, int]:
        """Per-class discriminator scores (at the final bleaching threshold)
        plus the threshold used, for a single raw feature row."""
        if not self._is_fitted:
            raise ValueError("Model must be fitted before scoring")
        evidence = self.model.scores(X)[0]
        return {k: evidence[k] for k in ("Cloud", "Edge", "threshold")}


def create_wisard_offloading_policy(
    config: Optional[WiSARDOffloadingConfig] = None,
) -> WiSARDOffloadingPolicy:
    """Factory function to create a WiSARD offloading policy.

    The returned policy must be fitted via fit_model() on the training
    split before predict() is called.
    """
    return WiSARDOffloadingPolicy(config or WiSARDOffloadingConfig())
