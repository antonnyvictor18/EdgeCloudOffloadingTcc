"""Representative workload evaluation for MLP_final_6 Edge/Cloud decisions.

This experiment creates a fixed, representative workload containing both Edge and Cloud
samples from the validation set, then evaluates the frozen MLP model's decision
capability without altering the model or workload selection based on results.

Methodology:
1. Define workload selection rule using validation set (50% Edge, 50% Cloud)
2. Freeze the selected workload (record sample IDs)
3. Evaluate MLP predictions on this fixed workload
4. Execute Edge-predicted tasks in EdgeSimPy
5. Mark Cloud-predicted tasks as CLOUD_UNAVAILABLE
6. Compare with NearestServerPolicy as Edge-only control

IMPORTANT: This evaluation uses validation set for workload selection to avoid
test set contamination. The test set remains untouched for final evaluation.
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, Simulator, User
from integration import TaskSchedulerIntegration
from models import Task, TaskStatus
from execution.task_scheduler import TaskScheduler
from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from policies import NearestServerPolicy
from policies.ml_offloading import CloudUnavailableStatus, MLPOffloadingPolicy, create_mlp_offloading_policy


@dataclass(frozen=True)
class RepresentativeWorkloadConfig:
    """Configuration for representative workload evaluation."""

    experiment_id: str = "mlp_representative_workload_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    user_id: int = 1
    candidate_server_ids: tuple[int, int] = (2, 5)
    delay_unit: str = "ms"
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"

    # Task parameters for EdgeSimPy execution
    task_data_size_mb: float = 0.1
    task_cpu_cycles: float = 100.0
    task_required_memory_mb: float = 100.0
    task_deadline_ms: float = 20_000.0
    task_latency_sensitivity: float = 0.5
    processing_rate_cycles_per_second: float = 50.0

    # Workload selection
    workload_size: int = 20  # Fixed workload size
    selection_seed: int = 20261001  # Seed for workload selection
    edge_ratio: float = 0.5  # Target 50% Edge, 50% Cloud

    # Model parameters
    model_path: Optional[Path] = None


@dataclass
class TaskEvaluationResult:
    """Results for one task in the representative workload."""

    task_id: str
    sample_id: int  # Original dataset sample ID
    analytical_label: str  # Ground truth from dataset
    mlp_prediction: str  # MLP prediction
    execution_status: str  # "EXECUTED", "CLOUD_UNAVAILABLE", "FAILED"
    selected_edge_server_id: Optional[int] = None
    features_used: Optional[Dict[str, float]] = None

    # Network metrics (if Edge execution)
    path: Optional[tuple[int, ...]] = None
    hops: Optional[int] = None
    path_delay_ms: Optional[float] = None
    transmission_time_s: Optional[float] = None
    propagation_delay_s: Optional[float] = None
    derived_communication_latency_s: Optional[float] = None

    # Execution metrics (if Edge execution)
    queue_time_s: Optional[float] = None
    execution_time_s: Optional[float] = None
    completion_time_s: Optional[float] = None
    deadline_violation: Optional[bool] = None


@dataclass
class RepresentativeWorkloadResults:
    """Results from representative workload evaluation."""

    config: RepresentativeWorkloadConfig
    workload_sample_ids: List[int] = field(default_factory=list)
    workload_labels: List[str] = field(default_factory=list)
    task_results: List[TaskEvaluationResult] = field(default_factory=list)

    # Predictive metrics
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    accuracy: float = 0.0
    edge_precision: float = 0.0
    edge_recall: float = 0.0
    edge_f1: float = 0.0
    cloud_precision: float = 0.0
    cloud_recall: float = 0.0
    cloud_f1: float = 0.0

    # Coverage metrics
    prediction_edge_rate: float = 0.0
    prediction_cloud_rate: float = 0.0
    execution_coverage: float = 0.0

    # Systemic metrics (for Edge-executed tasks only)
    systemic_metrics: Dict[str, Any] = field(default_factory=dict)

    summary: Dict[str, Any] = field(default_factory=dict)


class RepresentativeWorkloadEvaluator:
    """Evaluates MLP on a representative workload with both Edge and Cloud cases."""

    def __init__(self, config: RepresentativeWorkloadConfig):
        self.config = config
        self.results = RepresentativeWorkloadResults(config=config)

    def run_evaluation(self) -> RepresentativeWorkloadResults:
        """Run the complete representative workload evaluation."""
        print("="*70)
        print("MLP Representative Workload Evaluation")
        print("="*70)
        print(f"Workload size: {self.config.workload_size}")
        print(f"Target composition: {self.config.edge_ratio:.0%} Edge, {1-self.config.edge_ratio:.0%} Cloud")

        # Step 1: Create representative workload from validation set
        self._create_representative_workload()

        # Step 2: Load MLP model
        mlp_policy = self._load_mlp_policy()

        # Step 3: Evaluate MLP predictions on workload
        self._evaluate_mlp_predictions(mlp_policy)

        # Step 4: Execute Edge-predicted tasks in EdgeSimPy
        self._execute_edge_tasks()

        # Step 5: Calculate metrics
        self._calculate_metrics()

        # Step 6: Run NearestServerPolicy control
        self._run_nearest_control()

        return self.results

    def _create_representative_workload(self) -> None:
        """Create a fixed representative workload using validation set."""
        print("\n" + "="*60)
        print("Step 1: Creating Representative Workload")
        print("="*60)

        # Load dataset
        repository_root = Path(__file__).resolve().parents[2]
        dataset_path = repository_root / "Dataset" / "dataset.csv"
        dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

        print(f"Dataset loaded: {dataset.metadata.sample_count} samples")
        print(f"Validation set: {len(dataset.validation.y)} samples")

        # Get validation set labels and sample IDs
        val_labels = dataset.validation.y
        val_sample_ids = dataset.validation.sample_ids
        val_features = dataset.validation.X

        # Separate by class
        edge_indices = [i for i, label in enumerate(val_labels) if label == "Edge"]
        cloud_indices = [i for i, label in enumerate(val_labels) if label == "Cloud"]

        print(f"Validation Edge samples: {len(edge_indices)}")
        print(f"Validation Cloud samples: {len(cloud_indices)}")

        # Calculate target counts
        target_edge_count = int(self.config.workload_size * self.config.edge_ratio)
        target_cloud_count = self.config.workload_size - target_edge_count

        print(f"Target workload: {target_edge_count} Edge, {target_cloud_count} Cloud")

        # Select samples using fixed seed (deterministic selection)
        random_gen = random.Random(self.config.selection_seed)

        # Shuffle indices for random selection
        random_gen.shuffle(edge_indices)
        random_gen.shuffle(cloud_indices)

        # Select samples
        selected_edge_indices = edge_indices[:target_edge_count]
        selected_cloud_indices = cloud_indices[:target_cloud_count]

        # Combine and sort by sample_id for consistency
        selected_indices = selected_edge_indices + selected_cloud_indices
        selected_indices.sort(key=lambda i: val_sample_ids[i])

        # Store workload information
        self.results.workload_sample_ids = [val_sample_ids[i] for i in selected_indices]
        self.results.workload_labels = [val_labels[i] for i in selected_indices]
        self.workload_features = [val_features[i] for i in selected_indices]
        self.workload_indices = selected_indices

        print(f"Selected workload sample IDs: {self.results.workload_sample_ids}")
        print(f"Selected workload labels: {self.results.workload_labels}")

        # Validate workload composition
        edge_count = sum(1 for label in self.results.workload_labels if label == "Edge")
        cloud_count = sum(1 for label in self.results.workload_labels if label == "Cloud")
        print(f"Final workload: {edge_count} Edge, {cloud_count} Cloud")

    def _load_mlp_policy(self) -> MLPOffloadingPolicy:
        """Load the frozen MLP model."""
        print("\n" + "="*60)
        print("Step 2: Loading Frozen MLP Model")
        print("="*60)

        if self.config.model_path is None:
            model_path = Path(__file__).resolve().parents[1] / "models" / "mlp_final_6"
        else:
            model_path = self.config.model_path

        print(f"Loading MLP model from: {model_path}")
        mlp_policy = create_mlp_offloading_policy(model_path=model_path)
        mlp_policy.load_model()
        print("MLP model loaded successfully (frozen)")
        return mlp_policy

    def _evaluate_mlp_predictions(self, mlp_policy: MLPOffloadingPolicy) -> None:
        """Evaluate MLP predictions on the representative workload."""
        print("\n" + "="*60)
        print("Step 3: Evaluating MLP Predictions")
        print("="*60)

        # Create simulator for the entire experiment (single context)
        self.simulator = Simulator()
        self.simulator.initialize(input_file=self.config.dataset)

        user = User.find_by_id(self.config.user_id)
        if user is None:
            raise ValueError(f"User {self.config.user_id} not found")

        # Create tasks from workload
        self.workload_tasks = []
        self.edge_tasks = []  # Tasks predicted as Edge
        self.cloud_tasks = []  # Tasks predicted as Cloud

        for i, (sample_id, label, features) in enumerate(zip(
            self.results.workload_sample_ids,
            self.results.workload_labels,
            self.workload_features
        )):
            # Create Task object with dataset features
            task = Task(
                task_id=f"task_{i:02d}",
                user=user,
                cpu_cycles=features[0],  # CpuCycles
                data_size_mb=features[1],  # TaskSizeMB
                latency_sensitivity=features[2],  # LatencySensitivity
                required_memory_mb=features[3],  # RequiredMemoryMB
                deadline_ms=self.config.task_deadline_ms,
                creation_time_s=0.0,
            )

            # Store task with metadata
            task_info = {
                "task": task,
                "sample_id": sample_id,
                "analytical_label": label,
                "features": features,
            }
            self.workload_tasks.append(task_info)

            # Make MLP prediction
            try:
                decision = mlp_policy.predict(task, self.simulator.topology)
                task_info["mlp_prediction"] = decision.predicted_destination
                task_info["features_used"] = decision.features_used

                print(f"Task {task.task_id} (sample {sample_id}): "
                      f"Label={label}, Prediction={decision.predicted_destination}")

                if decision.predicted_destination == "Cloud":
                    task_info["execution_status"] = CloudUnavailableStatus.CLOUD_UNAVAILABLE.value
                    self.cloud_tasks.append(task_info)
                else:
                    task_info["execution_status"] = "PENDING"
                    self.edge_tasks.append(task_info)

            except Exception as e:
                print(f"MLP prediction failed for {task.task_id}: {e}")
                task_info["mlp_prediction"] = "ERROR"
                task_info["execution_status"] = "PREDICTION_FAILED"
                task_info["features_used"] = None

        # Count predictions
        edge_predictions = sum(1 for t in self.workload_tasks if t.get("mlp_prediction") == "Edge")
        cloud_predictions = sum(1 for t in self.workload_tasks if t.get("mlp_prediction") == "Cloud")

        print(f"\nPrediction Summary:")
        print(f"  Edge predictions: {edge_predictions}")
        print(f"  Cloud predictions: {cloud_predictions}")

    def _execute_edge_tasks(self) -> None:
        """Execute Edge-predicted tasks in EdgeSimPy."""
        if not self.edge_tasks:
            print("\nNo Edge tasks to execute")
            return

        print("\n" + "="*60)
        print(f"Step 4: Executing {len(self.edge_tasks)} Edge Tasks")
        print("="*60)

        # Use the same simulator that was initialized in _evaluate_mlp_predictions
        # This ensures topology consistency
        execution_simulator = self.simulator

        # Create TaskScheduler
        task_scheduler = TaskScheduler(
            processing_rate_cycles_per_second=self.config.processing_rate_cycles_per_second
        )

        # Create scheduler integration with the existing simulator
        scheduler_integration = TaskSchedulerIntegration(
            task_scheduler=task_scheduler,
            simulator=execution_simulator
        )

        # Recreated tasks list (will be populated below)
        recreated_edge_tasks = []

        # Define resource management algorithm
        def resource_management_algorithm(parameters):
            scheduler_integration.step()

        # Define stopping criterion
        def stopping_criterion(model):
            max_steps = 1000
            return (all(t[0].status == TaskStatus.COMPLETED for t in recreated_edge_tasks)
                    or execution_simulator.schedule.steps >= max_steps)

        # Set the algorithms on the existing simulator
        execution_simulator.resource_management_algorithm = resource_management_algorithm
        execution_simulator.stopping_criterion = stopping_criterion

        # Get user and servers from the execution simulator (same topology)
        user = User.find_by_id(self.config.user_id)
        edge_servers = [EdgeServer.find_by_id(sid) for sid in self.config.candidate_server_ids]
        edge_servers = [s for s in edge_servers if s is not None]

        # Create NearestServerPolicy for EdgeServer selection
        nearest_policy = NearestServerPolicy(topology=execution_simulator.topology)

        # Recreate and submit Edge tasks
        for task_info in self.edge_tasks:
            task = task_info["task"]

            # Select server using NearestServerPolicy
            try:
                selected_server = nearest_policy.select_server(task, edge_servers)
                task_info["selected_server_id"] = selected_server.id

                # Recreate task in execution simulator context
                new_task = Task(
                    task_id=task.task_id,
                    user=user,
                    cpu_cycles=self.config.task_cpu_cycles,  # Use config value for execution
                    data_size_mb=self.config.task_data_size_mb,
                    deadline_ms=task.deadline_ms,
                    latency_sensitivity=task.latency_sensitivity,
                    required_memory_mb=task.required_memory_mb,
                    creation_time_s=0.0,
                )
                new_task.target_server = selected_server
                recreated_edge_tasks.append((new_task, task_info, selected_server))
                scheduler_integration.submit_task(new_task, selected_server)

                print(f"Task {new_task.task_id}: Selected server {selected_server.id}")

            except Exception as e:
                print(f"Server selection failed for {task.task_id}: {e}")
                task_info["execution_status"] = "SERVER_SELECTION_FAILED"

        # Run simulation
        if recreated_edge_tasks:
            print("Running EdgeSimPy simulation...")
            execution_simulator.run_model()
            print(f"Simulation completed in {execution_simulator.schedule.steps} steps")

            # Collect results for executed tasks
            for new_task, task_info, selected_server in recreated_edge_tasks:
                if new_task.status == TaskStatus.COMPLETED:
                    task_info["execution_status"] = "EXECUTED"
                    task_info["task"] = new_task  # Update with executed task
                else:
                    task_info["execution_status"] = "EXECUTION_FAILED"

            # Calculate network metrics for executed tasks
            for new_task, task_info, selected_server in recreated_edge_tasks:
                if task_info["execution_status"] == "EXECUTED":
                    try:
                        import networkx as nx
                        user_switch = new_task.user.base_station.network_switch
                        server_switch = selected_server.base_station.network_switch
                        path = nx.shortest_path(
                            G=execution_simulator.topology,
                            source=user_switch,
                            target=server_switch,
                            weight="delay",
                            method="dijkstra",
                        )
                        path_delay_ms = execution_simulator.topology.calculate_path_delay(path=list(path))

                        task_info["network_metrics"] = {
                            "path": tuple(n.id for n in path),
                            "hops": len(path) - 1,
                            "path_delay_ms": path_delay_ms,
                            "propagation_delay_s": path_delay_ms / 1000.0,
                        }
                    except Exception as e:
                        print(f"Path calculation failed for {new_task.task_id}: {e}")
                        task_info["network_metrics"] = None

    def _calculate_metrics(self) -> None:
        """Calculate predictive and systemic metrics."""
        print("\n" + "="*60)
        print("Step 5: Calculating Metrics")
        print("="*60)

        # Convert task results to TaskEvaluationResult objects
        for task_info in self.workload_tasks:
            task = task_info["task"]
            result = TaskEvaluationResult(
                task_id=task.task_id,
                sample_id=task_info["sample_id"],
                analytical_label=task_info["analytical_label"],
                mlp_prediction=task_info.get("mlp_prediction", "ERROR"),
                execution_status=task_info.get("execution_status", "UNKNOWN"),
                selected_edge_server_id=task_info.get("selected_server_id"),
                features_used=task_info.get("features_used"),
            )

            # Add network metrics if available
            if "network_metrics" in task_info and task_info["network_metrics"]:
                metrics = task_info["network_metrics"]
                result.path = metrics["path"]
                result.hops = metrics["hops"]
                result.path_delay_ms = metrics["path_delay_ms"]
                result.propagation_delay_s = metrics["propagation_delay_s"]

            # Add execution metrics if available
            if task_info["execution_status"] == "EXECUTED":
                result.transmission_time_s = task.transmission_time_s
                result.queue_time_s = task.queue_time_s
                result.execution_time_s = task.execution_time_s
                result.completion_time_s = task.completion_time_s
                result.deadline_violation = task.deadline_violation
                if result.propagation_delay_s is not None and result.transmission_time_s is not None:
                    result.derived_communication_latency_s = (
                        result.transmission_time_s + result.propagation_delay_s
                    )

            self.results.task_results.append(result)

        # Calculate confusion matrix
        self._calculate_confusion_matrix()

        # Calculate coverage metrics
        total_tasks = len(self.results.task_results)
        edge_predictions = sum(1 for r in self.results.task_results if r.mlp_prediction == "Edge")
        cloud_predictions = sum(1 for r in self.results.task_results if r.mlp_prediction == "Cloud")
        executed_tasks = sum(1 for r in self.results.task_results if r.execution_status == "EXECUTED")

        self.results.prediction_edge_rate = edge_predictions / total_tasks if total_tasks > 0 else 0
        self.results.prediction_cloud_rate = cloud_predictions / total_tasks if total_tasks > 0 else 0
        self.results.execution_coverage = executed_tasks / total_tasks if total_tasks > 0 else 0

        # Calculate systemic metrics for executed tasks
        self._calculate_systemic_metrics()

        print(f"Metrics calculated:")
        print(f"  Prediction Edge rate: {self.results.prediction_edge_rate:.1%}")
        print(f"  Prediction Cloud rate: {self.results.prediction_cloud_rate:.1%}")
        print(f"  Execution coverage: {self.results.execution_coverage:.1%}")

    def _calculate_confusion_matrix(self) -> None:
        """Calculate confusion matrix for MLP predictions."""
        # Initialize confusion matrix
        self.results.confusion_matrix = {
            "Edge": {"Edge": 0, "Cloud": 0},
            "Cloud": {"Edge": 0, "Cloud": 0},
        }

        # Count predictions vs labels
        for result in self.results.task_results:
            true_label = result.analytical_label
            predicted = result.mlp_prediction

            if true_label in self.results.confusion_matrix and predicted in self.results.confusion_matrix[true_label]:
                self.results.confusion_matrix[true_label][predicted] += 1

        # Calculate metrics
        tp_edge = self.results.confusion_matrix["Edge"]["Edge"]
        fp_edge = self.results.confusion_matrix["Cloud"]["Edge"]
        fn_edge = self.results.confusion_matrix["Edge"]["Cloud"]
        tn_edge = self.results.confusion_matrix["Cloud"]["Cloud"]

        # Edge metrics
        self.results.edge_precision = tp_edge / (tp_edge + fp_edge) if (tp_edge + fp_edge) > 0 else 0
        self.results.edge_recall = tp_edge / (tp_edge + fn_edge) if (tp_edge + fn_edge) > 0 else 0
        self.results.edge_f1 = (
            2 * (self.results.edge_precision * self.results.edge_recall) /
            (self.results.edge_precision + self.results.edge_recall)
            if (self.results.edge_precision + self.results.edge_recall) > 0 else 0
        )

        # Cloud metrics
        self.results.cloud_precision = tn_edge / (tn_edge + fn_edge) if (tn_edge + fn_edge) > 0 else 0
        self.results.cloud_recall = tn_edge / (tn_edge + fp_edge) if (tn_edge + fp_edge) > 0 else 0
        self.results.cloud_f1 = (
            2 * (self.results.cloud_precision * self.results.cloud_recall) /
            (self.results.cloud_precision + self.results.cloud_recall)
            if (self.results.cloud_precision + self.results.cloud_recall) > 0 else 0
        )

        # Overall accuracy
        correct = tp_edge + tn_edge
        total = sum(sum(row.values()) for row in self.results.confusion_matrix.values())
        self.results.accuracy = correct / total if total > 0 else 0

    def _calculate_systemic_metrics(self) -> None:
        """Calculate systemic metrics for executed tasks."""
        executed_results = [r for r in self.results.task_results if r.execution_status == "EXECUTED"]

        if not executed_results:
            self.results.systemic_metrics = {"executed_tasks": 0}
            return

        # Extract metrics
        transmission_times = [r.transmission_time_s for r in executed_results if r.transmission_time_s is not None]
        propagation_delays = [r.propagation_delay_s for r in executed_results if r.propagation_delay_s is not None]
        queue_times = [r.queue_time_s for r in executed_results if r.queue_time_s is not None]
        execution_times = [r.execution_time_s for r in executed_results if r.execution_time_s is not None]
        completion_times = [r.completion_time_s for r in executed_results if r.completion_time_s is not None]
        deadline_violations = [r.deadline_violation for r in executed_results if r.deadline_violation is not None]

        self.results.systemic_metrics = {
            "executed_tasks": len(executed_results),
            "mean_transmission_time_s": np.mean(transmission_times) if transmission_times else None,
            "mean_propagation_delay_s": np.mean(propagation_delays) if propagation_delays else None,
            "mean_queue_time_s": np.mean(queue_times) if queue_times else None,
            "mean_execution_time_s": np.mean(execution_times) if execution_times else None,
            "mean_completion_time_s": np.mean(completion_times) if completion_times else None,
            "p95_completion_time_s": np.percentile(completion_times, 95) if len(completion_times) >= 20 else None,
            "max_completion_time_s": max(completion_times) if completion_times else None,
            "deadline_violation_count": sum(deadline_violations),
            "deadline_violation_rate": sum(deadline_violations) / len(deadline_violations) if deadline_violations else None,
        }

    def _run_nearest_control(self) -> None:
        """Run NearestServerPolicy as Edge-only control on the same workload."""
        print("\n" + "="*60)
        print("Step 6: NearestServerPolicy Control")
        print("="*60)

        # Use the same simulator that was used for MLP evaluation
        # This ensures consistency in topology and component references
        user = User.find_by_id(self.config.user_id)
        edge_servers = [EdgeServer.find_by_id(sid) for sid in self.config.candidate_server_ids]
        edge_servers = [s for s in edge_servers if s is not None]

        nearest_policy = NearestServerPolicy(topology=self.simulator.topology)

        # Run all tasks through NearestServerPolicy (always Edge)
        nearest_results = []
        for task_info in self.workload_tasks:
            task = task_info["task"]

            # Create fresh task for control (using same topology)
            control_task = Task(
                task_id=f"control_{task.task_id}",
                user=user,
                cpu_cycles=self.config.task_cpu_cycles,
                data_size_mb=self.config.task_data_size_mb,
                deadline_ms=task.deadline_ms,
                latency_sensitivity=task.latency_sensitivity,
                required_memory_mb=task.required_memory_mb,
                creation_time_s=0.0,
            )

            try:
                selected_server = nearest_policy.select_server(control_task, edge_servers)
                nearest_results.append({
                    "task_id": task.task_id,
                    "sample_id": task_info["sample_id"],
                    "analytical_label": task_info["analytical_label"],
                    "selected_server_id": selected_server.id,
                })
            except Exception as e:
                print(f"Nearest selection failed for {task.task_id}: {e}")

        self.results.summary["nearest_control"] = {
            "total_tasks": len(nearest_results),
            "edge_selections": len(nearest_results),  # Always Edge
            "server_distribution": self._count_server_distribution(nearest_results),
        }

        print(f"NearestServerPolicy selected servers for {len(nearest_results)} tasks")

    def _count_server_distribution(self, results: List[Dict[str, Any]]) -> Dict[int, int]:
        """Count server selection distribution."""
        distribution = {}
        for result in results:
            server_id = result["selected_server_id"]
            distribution[server_id] = distribution.get(server_id, 0) + 1
        return distribution

    def generate_report(self, output_path: Path) -> None:
        """Generate comprehensive markdown report."""
        lines = [
            "# MLP Representative Workload Evaluation Report",
            "",
            "## Objective",
            "",
            "Evaluate MLP_final_6 on a representative workload containing both Edge and Cloud",
            "cases to test the model's Edge/Cloud decision capability without altering the model.",
            "",
            "## Methodology",
            "",
            "- Workload selected from validation set (not test set)",
            "- Fixed composition: 50% Edge, 50% Cloud",
            "- Frozen MLP model (no retraining)",
            "- Edge-predicted tasks executed in EdgeSimPy",
            "- Cloud-predicted tasks marked CLOUD_UNAVAILABLE",
            "- NearestServerPolicy used as Edge-only control",
            "",
            "## Configuration",
            "",
            f"- **Experiment ID**: {self.results.config.experiment_id}",
            f"- **Workload Size**: {self.results.config.workload_size}",
            f"- **Selection Seed**: {self.results.config.selection_seed}",
            f"- **User ID**: {self.results.config.user_id}",
            f"- **Candidate Servers**: {self.results.config.candidate_server_ids}",
            f"- **Processing Rate**: {self.results.config.processing_rate_cycles_per_second} cycles/s",
            "",
            "## Workload Composition",
            "",
            f"- **Total Tasks**: {len(self.results.workload_sample_ids)}",
            f"- **Sample IDs**: {self.results.workload_sample_ids}",
            f"- **Edge Labels**: {self.results.workload_labels.count('Edge')}",
            f"- **Cloud Labels**: {self.results.workload_labels.count('Cloud')}",
            "",
            "## Predictive Performance",
            "",
            f"- **Accuracy**: {self.results.accuracy:.3f}",
            f"- **Edge Precision**: {self.results.edge_precision:.3f}",
            f"- **Edge Recall**: {self.results.edge_recall:.3f}",
            f"- **Edge F1**: {self.results.edge_f1:.3f}",
            f"- **Cloud Precision**: {self.results.cloud_precision:.3f}",
            f"- **Cloud Recall**: {self.results.cloud_recall:.3f}",
            f"- **Cloud F1**: {self.results.cloud_f1:.3f}",
            "",
            "### Confusion Matrix",
            "",
            "| | Predicted Edge | Predicted Cloud |",
            "|---|---|---|",
            f"| **Actual Edge** | {self.results.confusion_matrix['Edge']['Edge']} | {self.results.confusion_matrix['Edge']['Cloud']} |",
            f"| **Actual Cloud** | {self.results.confusion_matrix['Cloud']['Edge']} | {self.results.confusion_matrix['Cloud']['Cloud']} |",
            "",
            "## Coverage Metrics",
            "",
            f"- **Prediction Edge Rate**: {self.results.prediction_edge_rate:.1%}",
            f"- **Prediction Cloud Rate**: {self.results.prediction_cloud_rate:.1%}",
            f"- **Execution Coverage**: {self.results.execution_coverage:.1%}",
            "",
            "Note: Execution coverage is not directly comparable to Edge-only policies",
            "when Cloud infrastructure is unavailable.",
            "",
            "## Task-Level Results",
            "",
            "### Table A: Decision Results",
            "",
            "| Task | Sample ID | Label | Prediction | Status | Server |",
            "|------|-----------|-------|------------|--------|--------|",
        ]

        # Add task results
        for result in self.results.task_results:
            server = result.selected_edge_server_id if result.selected_edge_server_id else "N/A"
            lines.append(
                f"| {result.task_id} | {result.sample_id} | {result.analytical_label} | "
                f"{result.mlp_prediction} | {result.execution_status} | {server} |"
            )

        lines.extend([
            "",
            "### Table B: Execution Metrics (Edge Tasks Only)",
            "",
            "| Task | Server | Transmission | Propagation | Queue | Execution | Completion | Deadline Violation |",
            "|------|--------|--------------|-------------|-------|-----------|------------|-------------------|",
        ])

        # Add execution metrics for executed tasks
        for result in self.results.task_results:
            if result.execution_status == "EXECUTED":
                transmission = f"{result.transmission_time_s:.2f}" if result.transmission_time_s else "N/A"
                propagation = f"{result.propagation_delay_s:.3f}" if result.propagation_delay_s else "N/A"
                queue = f"{result.queue_time_s:.2f}" if result.queue_time_s else "N/A"
                execution = f"{result.execution_time_s:.2f}" if result.execution_time_s else "N/A"
                completion = f"{result.completion_time_s:.2f}" if result.completion_time_s else "N/A"
                deadline = "Yes" if result.deadline_violation else "No"

                lines.append(
                    f"| {result.task_id} | {result.selected_edge_server_id} | {transmission} | "
                    f"{propagation} | {queue} | {execution} | {completion} | {deadline} |"
                )

        lines.extend([
            "",
            "## Systemic Metrics (Edge-Executed Tasks)",
            "",
        ])

        # Add systemic metrics
        if self.results.systemic_metrics["executed_tasks"] > 0:
            metrics = self.results.systemic_metrics
            lines.extend([
                f"- **Executed Tasks**: {metrics['executed_tasks']}",
                f"- **Mean Transmission Time**: {metrics.get('mean_transmission_time_s', 'N/A'):.2f} s",
                f"- **Mean Propagation Delay**: {metrics.get('mean_propagation_delay_s', 'N/A'):.3f} s",
                f"- **Mean Queue Time**: {metrics.get('mean_queue_time_s', 'N/A'):.2f} s",
                f"- **Mean Execution Time**: {metrics.get('mean_execution_time_s', 'N/A'):.2f} s",
                f"- **Mean Completion Time**: {metrics.get('mean_completion_time_s', 'N/A'):.2f} s",
                f"- **P95 Completion Time**: {metrics.get('p95_completion_time_s', 'N/A')}",
                f"- **Max Completion Time**: {metrics.get('max_completion_time_s', 'N/A'):.2f} s",
                f"- **Deadline Violations**: {metrics.get('deadline_violation_count', 0)}",
                f"- **Deadline Violation Rate**: {metrics.get('deadline_violation_rate', 'N/A'):.1%}",
            ])
        else:
            lines.append("No tasks were executed (all predicted as Cloud or failed)")

        lines.extend([
            "",
            "## NearestServerPolicy Control",
            "",
        ])

        # Add control results
        if "nearest_control" in self.results.summary:
            control = self.results.summary["nearest_control"]
            lines.extend([
                f"- **Tasks Processed**: {control['total_tasks']}",
                f"- **Edge Selections**: {control['edge_selections']} (always Edge)",
                f"- **Server Distribution**: {control['server_distribution']}",
            ])

        lines.extend([
            "",
            "## Analysis",
            "",
            "### Label Distribution",
            f"- Edge labels: {self.results.workload_labels.count('Edge')}/{len(self.results.workload_labels)} "
            f"({self.results.workload_labels.count('Edge')/len(self.results.workload_labels):.1%})",
            f"- Cloud labels: {self.results.workload_labels.count('Cloud')}/{len(self.results.workload_labels)} "
            f"({self.results.workload_labels.count('Cloud')/len(self.results.workload_labels):.1%})",
            "",
            "### Prediction Distribution",
            f"- Edge predictions: {sum(1 for r in self.results.task_results if r.mlp_prediction == 'Edge')}/{len(self.results.task_results)} "
            f"({self.results.prediction_edge_rate:.1%})",
            f"- Cloud predictions: {sum(1 for r in self.results.task_results if r.mlp_prediction == 'Cloud')}/{len(self.results.task_results)} "
            f"({self.results.prediction_cloud_rate:.1%})",
            "",
            "### Error Analysis",
            f"- Edge → Cloud errors: {self.results.confusion_matrix['Edge']['Cloud']} "
            f"(Cloud predicted for Edge tasks)",
            f"- Cloud → Edge errors: {self.results.confusion_matrix['Cloud']['Edge']} "
            f"(Edge predicted for Cloud tasks)",
            "",
            "### CLOUD_UNAVAILABLE Effect",
            f"- Tasks marked CLOUD_UNAVAILABLE: {sum(1 for r in self.results.task_results if r.execution_status == 'CLOUD_UNAVAILABLE')}",
            f"- These tasks cannot be executed without Cloud infrastructure",
            "",
            "### Edge Execution",
            f"- Tasks executed in EdgeSimPy: {self.results.systemic_metrics.get('executed_tasks', 0)}",
            f"- Server selection delegated to NearestServerPolicy",
            "",
            "## Limitations",
            "",
            "1. **Cloud Infrastructure**: Cloud is not implemented in EdgeSimPy, so Cloud-predicted",
            "   tasks cannot be executed and are marked CLOUD_UNAVAILABLE.",
            "2. **Execution Coverage**: The execution coverage metric is diagnostic only - it shows",
            "   how much workload can be processed with current infrastructure, not policy quality.",
            "3. **Global Network Features**: NetworkLatencyMs and BandwidthMbps are calculated as",
            "   global features across all EdgeServers, matching the C# dataset semantics.",
            "4. **Representative Workload**: This workload was selected from validation set using",
            "   a fixed rule before evaluation. Results should not be generalized to the full test set.",
            "",
            "## Next Steps",
            "",
            "1. Implement Cloud infrastructure in EdgeSimPy to execute Cloud-predicted tasks",
            "2. Evaluate on full test set for final model assessment",
            "3. Compare MLP performance against Edge-only policies with Cloud implementation",
            "4. Analyze system-level impact of Edge/Cloud decisions on latency and resource utilization",
        ])

        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"\nReport saved to: {output_path}")

    def save_results_json(self, output_path: Path) -> None:
        """Save results as JSON for programmatic access."""
        results_dict = {
            "config": {
                "experiment_id": self.results.config.experiment_id,
                "workload_size": self.results.config.workload_size,
                "selection_seed": self.results.config.selection_seed,
                "user_id": self.results.config.user_id,
                "candidate_server_ids": self.results.config.candidate_server_ids,
            },
            "workload": {
                "sample_ids": self.results.workload_sample_ids,
                "labels": self.results.workload_labels,
            },
            "predictive_metrics": {
                "accuracy": self.results.accuracy,
                "edge_precision": self.results.edge_precision,
                "edge_recall": self.results.edge_recall,
                "edge_f1": self.results.edge_f1,
                "cloud_precision": self.results.cloud_precision,
                "cloud_recall": self.results.cloud_recall,
                "cloud_f1": self.results.cloud_f1,
                "confusion_matrix": self.results.confusion_matrix,
            },
            "coverage_metrics": {
                "prediction_edge_rate": self.results.prediction_edge_rate,
                "prediction_cloud_rate": self.results.prediction_cloud_rate,
                "execution_coverage": self.results.execution_coverage,
            },
            "systemic_metrics": self.results.systemic_metrics,
            "task_results": [
                {
                    "task_id": r.task_id,
                    "sample_id": r.sample_id,
                    "analytical_label": r.analytical_label,
                    "mlp_prediction": r.mlp_prediction,
                    "execution_status": r.execution_status,
                    "selected_edge_server_id": r.selected_edge_server_id,
                    "transmission_time_s": r.transmission_time_s,
                    "propagation_delay_s": r.propagation_delay_s,
                    "queue_time_s": r.queue_time_s,
                    "execution_time_s": r.execution_time_s,
                    "completion_time_s": r.completion_time_s,
                    "deadline_violation": r.deadline_violation,
                }
                for r in self.results.task_results
            ],
            "summary": self.results.summary,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results_dict, f, indent=2)

        print(f"JSON results saved to: {output_path}")


def main():
    """Main execution function."""
    config = RepresentativeWorkloadConfig()

    evaluator = RepresentativeWorkloadEvaluator(config)
    results = evaluator.run_evaluation()

    # Generate outputs
    results_dir = Path(__file__).resolve().parents[1] / "results"
    results_dir.mkdir(exist_ok=True)

    evaluator.generate_report(results_dir / "mlp_representative_workload.md")
    evaluator.save_results_json(results_dir / "mlp_representative_workload.json")

    print("\n" + "="*70)
    print("Evaluation Complete")
    print("="*70)
    print(f"Total tasks: {len(results.task_results)}")
    print(f"Edge predictions: {sum(1 for r in results.task_results if r.mlp_prediction == 'Edge')}")
    print(f"Cloud predictions: {sum(1 for r in results.task_results if r.mlp_prediction == 'Cloud')}")
    print(f"Executed tasks: {results.systemic_metrics.get('executed_tasks', 0)}")
    print(f"Accuracy: {results.accuracy:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())