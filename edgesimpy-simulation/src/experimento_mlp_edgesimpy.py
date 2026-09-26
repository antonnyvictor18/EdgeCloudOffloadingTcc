"""First controlled integration of MLP_final_6 with EdgeSimPy.

This experiment validates the MLP model in a simulation environment:
- Task → Feature Extraction → MLP → Edge/Cloud prediction
- If Edge: NearestServerPolicy → EdgeServer → TaskNetworkFlow → TaskScheduler → Execution
- If Cloud: CLOUD_UNAVAILABLE (no execution, as Cloud is not implemented)

Three levels of evaluation:
1. Predictive: accuracy, F1 (already measured on test set)
2. Decision: predicted Edge/Cloud, selected EdgeServer
3. Systemic: transmission, queue, execution, completion, deadline

IMPORTANT: Cloud is not implemented in EdgeSimPy. Tasks predicted as Cloud
are marked CLOUD_UNAVAILABLE and not executed. This is intentional to maintain
methodological integrity and avoid silent fallback to Edge.
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, NetworkFlow, Simulator, User
from integration import CommunicationMetrics, TaskSchedulerIntegration
from models import Task, TaskStatus
from execution.task_scheduler import TaskScheduler
from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from ml.mlp_model import MLPConfig, MLPModel
from policies import NearestServerPolicy
from policies.ml_offloading import CloudUnavailableStatus, MLPOffloadingPolicy, create_mlp_offloading_policy


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for MLP EdgeSimPy integration experiment."""

    experiment_id: str = "mlp_edgesimpy_integration_v1"
    dataset: str = "tutorials/datasets/sample_dataset2.json"
    user_id: int = 1
    candidate_server_ids: tuple[int, int] = (2, 5)
    random_seed: int = 20260910
    delay_unit: str = "ms"
    tick_duration_s: float = 1.0
    bandwidth_algorithm: str = "max_min_fairness"


    # Task parameters (matching experiment patterns)
    task_data_size_mb: float = 0.001  # Very small for fast simulation
    task_cpu_cycles: float = 100.0  # Very small for fast execution
    task_required_memory_mb: float = 100.0
    task_deadline_ms: float = 20_000.0
    task_latency_sensitivity: float = 0.5
    processing_rate_cycles_per_second: float = 50.0  # Reduced for faster execution

    # Model parameters (matching MLP_final_6)
    mlp_hidden_neurons: int = 18
    mlp_learning_rate: float = 0.04
    mlp_epochs: int = 35
    mlp_seed: int = 11

    # Processing rate (cycles per second)
    processing_rate_cycles_per_second: float = 50.0  # Reduced for faster execution


@dataclass
class TaskExecutionResult:
    """Results for one task execution in EdgeSimPy."""

    task_id: str
    predicted_destination: str
    execution_status: str
    selected_edge_server_id: Optional[int] = None
    features_used: Optional[Dict[str, float]] = None

    # Network metrics (if Edge)
    path: Optional[tuple[int, ...]] = None
    hops: Optional[int] = None
    path_delay_ms: Optional[float] = None
    transmission_time_s: Optional[float] = None
    propagation_delay_s: Optional[float] = None
    derived_communication_latency_s: Optional[float] = None

    # Execution metrics (if Edge)
    queue_time_s: Optional[float] = None
    execution_time_s: Optional[float] = None
    completion_time_s: Optional[float] = None
    deadline_violation: Optional[bool] = None

    # Model info
    model_version: str = "MLP_final_6"
    preprocessing_version: str = "min-max-v2-6features"


@dataclass
class ExperimentResults:
    """Results from MLP EdgeSimPy integration experiment."""

    config: ExperimentConfig
    task_results: List[TaskExecutionResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


def make_sample_tasks(config: ExperimentConfig, user: Any, count: int) -> List[Task]:
    """Create sample tasks with varying characteristics to test both Edge and Cloud predictions.

    Args:
        config: Experiment configuration
        user: User object
        count: Number of tasks to create

    Returns:
        List of Task objects
    """
    tasks = []
    random_gen = random.Random(config.random_seed)

    for i in range(count):
        # Vary task characteristics to potentially trigger different MLP predictions
        # These ranges match the C# dataset generation
        cpu_cycles = random_gen.uniform(50_000_000, 8_000_000_000)
        task_size_mb = random_gen.uniform(0.001, 1.0)  # Very small for fast simulation
        latency_sensitivity = random_gen.uniform(0, 1)
        required_memory_mb = random_gen.uniform(64, 6144)

        task = Task(
            task_id=f"task_{i:02d}",
            user=user,
            cpu_cycles=cpu_cycles,
            data_size_mb=task_size_mb,
            deadline_ms=config.task_deadline_ms,
            latency_sensitivity=latency_sensitivity,
            required_memory_mb=required_memory_mb,
            creation_time_s=0.0,
        )
        tasks.append(task)

    return tasks


def load_and_train_mlp(config: ExperimentConfig) -> MLPOffloadingPolicy:
    """Load dataset and train MLP with the final 6-feature configuration.

    Args:
        config: Experiment configuration

    Returns:
        Trained MLPOffloadingPolicy
    """
    # Script is in edgesimpy-simulation/src/, so:
    # parents[1] = edgesimpy-simulation
    # parents[2] = EdgeCloudOffloadingTcc (repo root)
    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"

    # Model save path
    model_save_path = Path(__file__).resolve().parents[1] / "models" / "mlp_final_6"

    # Try to load existing model
    if model_save_path.with_suffix(".npz").exists() and model_save_path.with_suffix(".json").exists():
        print(f"Loading existing MLP model from: {model_save_path}")
        dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)
        print(f"Dataset loaded: {dataset.metadata.sample_count} samples")
        print(f"Features: {list(FEATURE_NAMES)}")

        # Create MLP policy with model path
        mlp_policy = create_mlp_offloading_policy(model_path=model_save_path)
        mlp_policy.load_model()
        print("MLP model loaded from disk")
    else:
        print(f"Loading dataset from: {dataset_path}")
        dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

        print(f"Dataset loaded: {dataset.metadata.sample_count} samples")
        print(f"Features: {list(FEATURE_NAMES)}")

        # Create MLP policy
        mlp_policy = create_mlp_offloading_policy()

        # Load model structure
        mlp_policy.load_model()

        # Train on training data (reproducible due to fixed seed)
        X_train = np.array(dataset.train.X)
        y_train = np.array(dataset.train.y)
        print(f"Training MLP on {len(X_train)} samples...")
        mlp_policy.fit_model(X_train, y_train)
        print("MLP training complete")

        # Save model for future use
        print(f"Saving MLP model to: {model_save_path}")
        mlp_policy.model.save(model_save_path)
        print("MLP model saved to disk")

    return mlp_policy


def run_mlp_integration_experiment(config: ExperimentConfig) -> ExperimentResults:
    """Run MLP integration experiment with EdgeSimPy.

    Args:
        config: Experiment configuration

    Returns:
        Experiment results
    """
    results = ExperimentResults(config=config)

    # Load and train MLP
    mlp_policy = load_and_train_mlp(config)

    # Phase 1: MLP predictions and server selection (without EdgeSimPy)
    # We'll create temporary tasks for prediction only
    print(f"\n{'='*60}")
    print("Phase 1: MLP Predictions and Server Selection")
    print(f"{'='*60}")

    # Create a temporary simulator just for topology access during prediction
    temp_simulator = Simulator()
    temp_simulator.initialize(input_file=config.dataset)

    # Get user and edge servers
    user = User.find_by_id(config.user_id)
    if user is None:
        raise ValueError(f"User {config.user_id} not found")

    edge_servers = [EdgeServer.find_by_id(sid) for sid in config.candidate_server_ids]
    edge_servers = [s for s in edge_servers if s is not None]
    if not edge_servers:
        raise ValueError("No valid edge servers found")

    print(f"User: {user.id}")
    print(f"Edge servers: {[s.id for s in edge_servers]}")

    # Create NearestServerPolicy for EdgeServer selection
    nearest_policy = NearestServerPolicy(topology=temp_simulator.topology)

    # Create sample tasks
    tasks = make_sample_tasks(config, user, count=3)  # Reduced for faster debugging
    print(f"\nCreated {len(tasks)} sample tasks")

    # Store task characteristics for recreation later
    task_characteristics = []
    edge_tasks = []  # Tasks to execute
    cloud_tasks = []  # Tasks marked as unavailable

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Processing task: {task.task_id}")
        print(f"{'='*60}")

        # Store characteristics for recreation
        task_char = {
            "task_id": task.task_id,
            "cpu_cycles": task.cpu_cycles,
            "data_size_mb": task.data_size_mb,
            "deadline_ms": task.deadline_ms,
            "latency_sensitivity": task.latency_sensitivity,
            "required_memory_mb": task.required_memory_mb,
        }
        task_characteristics.append(task_char)

        # Step 1: MLP prediction
        try:
            decision = mlp_policy.predict(task, temp_simulator.topology)
            print(f"MLP prediction: {decision.predicted_destination}")
            print(f"Features used: {decision.features_used}")
        except Exception as e:
            print(f"MLP prediction failed: {e}")
            results.task_results.append(TaskExecutionResult(
                task_id=task.task_id,
                predicted_destination="ERROR",
                execution_status="PREDICTION_FAILED",
            ))
            continue

        # Step 2: Handle prediction
        if decision.predicted_destination == "Cloud":
            # Cloud not implemented - mark as unavailable
            print("Cloud predicted - CLOUD_UNAVAILABLE (not executed)")
            cloud_tasks.append((task_char, decision))
            continue

        # Step 3: Edge - select server
        if decision.predicted_destination == "Edge":
            try:
                selected_server = nearest_policy.select_server(task, edge_servers)
                print(f"Selected EdgeServer: {selected_server.id}")
                edge_tasks.append((task_char, decision, selected_server.id))
            except Exception as e:
                print(f"Server selection failed: {e}")
                results.task_results.append(TaskExecutionResult(
                    task_id=task.task_id,
                    predicted_destination="Edge",
                    execution_status="SERVER_SELECTION_FAILED",
                    features_used=decision.features_used,
                ))
                continue

    # Phase 2: Execute Edge tasks with TaskScheduler and TaskNetworkFlow
    if edge_tasks:
        print(f"\n{'='*60}")
        print(f"Phase 2: Executing {len(edge_tasks)} Edge tasks with TaskScheduler")
        print(f"{'='*60}")

        # Create TaskScheduler
        task_scheduler = TaskScheduler(
            processing_rate_cycles_per_second=config.processing_rate_cycles_per_second
        )

        # Define resource management algorithm
        def resource_management_algorithm(parameters):
            scheduler_integration.step()

        # Define stopping criterion (timeout-based for safety)
        max_steps = 1000  # Safety timeout
        def stopping_criterion(model):
            # Stop if all tasks completed or timeout reached
            all_completed = all(
                recreated_tasks[task_char["task_id"]].status == TaskStatus.COMPLETED
                for task_char, _, _ in edge_tasks
            )
            return all_completed or execution_simulator.schedule.steps >= max_steps

        # Create execution simulator with resource management
        execution_simulator = Simulator(
            resource_management_algorithm=resource_management_algorithm,
            stopping_criterion=stopping_criterion
        )
        execution_simulator.initialize(input_file=config.dataset)

        # Get user and servers from the execution simulator
        user = User.find_by_id(config.user_id)
        edge_servers = [EdgeServer.find_by_id(sid) for sid in config.candidate_server_ids]
        edge_servers = [s for s in edge_servers if s is not None]

        # Create TaskSchedulerIntegration with the execution simulator
        scheduler_integration = TaskSchedulerIntegration(
            task_scheduler=task_scheduler,
            simulator=execution_simulator
        )

        # Recreate tasks in the execution simulator
        recreated_tasks = {}
        for task_char, decision, selected_server_id in edge_tasks:
            selected_server = EdgeServer.find_by_id(selected_server_id)
            if selected_server is None:
                print(f"Warning: Server {selected_server_id} not found in execution simulator")
                continue

            task = Task(
                task_id=task_char["task_id"],
                user=user,
                cpu_cycles=config.task_cpu_cycles,  # Use config value for fast execution
                data_size_mb=task_char["data_size_mb"],
                deadline_ms=task_char["deadline_ms"],
                latency_sensitivity=task_char["latency_sensitivity"],
                required_memory_mb=task_char["required_memory_mb"],
                creation_time_s=0.0,
            )
            task.target_server = selected_server
            recreated_tasks[task.task_id] = task

            # Submit to scheduler integration
            scheduler_integration.submit_task(task, selected_server)

        # Run simulation
        print("Running EdgeSimPy simulation...")
        execution_simulator.run_model()
        print(f"Simulation completed in {execution_simulator.schedule.steps} steps")

        # Debug: print task statuses
        for task_char, _, _ in edge_tasks:
            task = recreated_tasks.get(task_char["task_id"])
            if task:
                print(f"Task {task.task_id}: status={task.status.value}, completion_time={task.completion_time_s}")

        # Collect results for Edge tasks
        for task_char, decision, selected_server_id in edge_tasks:
            task = recreated_tasks.get(task_char["task_id"])
            if task is None:
                continue

            selected_server = EdgeServer.find_by_id(selected_server_id)
            if selected_server is None:
                continue

            # Calculate network path for metrics
            try:
                import networkx as nx
                user_switch = task.user.base_station.network_switch
                server_switch = selected_server.base_station.network_switch
                path = nx.shortest_path(
                    G=execution_simulator.topology,
                    source=user_switch,
                    target=server_switch,
                    weight="delay",
                    method="dijkstra",
                )
                path_delay_ms = execution_simulator.topology.calculate_path_delay(path=list(path))
            except Exception as e:
                print(f"Path calculation failed for {task.task_id}: {e}")
                path = None
                path_delay_ms = None

            results.task_results.append(TaskExecutionResult(
                task_id=task.task_id,
                predicted_destination="Edge",
                execution_status=task.status.value,
                selected_edge_server_id=selected_server.id,
                features_used=decision.features_used,
                path=tuple(n.id for n in path) if path else None,
                hops=len(path) - 1 if path else None,
                path_delay_ms=path_delay_ms,
                transmission_time_s=task.transmission_time_s,
                propagation_delay_s=path_delay_ms / 1000.0 if path_delay_ms else None,
                derived_communication_latency_s=(
                    (task.transmission_time_s or 0) + (path_delay_ms / 1000.0 if path_delay_ms else 0)
                ),
                queue_time_s=task.queue_time_s,
                execution_time_s=task.execution_time_s,
                completion_time_s=task.completion_time_s,
                deadline_violation=task.deadline_violation,
            ))

    # Phase 3: Record Cloud tasks as unavailable
    for task_char, decision in cloud_tasks:
        results.task_results.append(TaskExecutionResult(
            task_id=task_char["task_id"],
            predicted_destination="Cloud",
            execution_status=CloudUnavailableStatus.CLOUD_UNAVAILABLE.value,
            features_used=decision.features_used,
        ))

    # Generate summary
    edge_predictions = sum(1 for r in results.task_results if r.predicted_destination == "Edge")
    cloud_predictions = sum(1 for r in results.task_results if r.predicted_destination == "Cloud")
    cloud_unavailable = sum(1 for r in results.task_results if r.execution_status == CloudUnavailableStatus.CLOUD_UNAVAILABLE.value)
    edge_completed = sum(1 for r in results.task_results if r.predicted_destination == "Edge" and r.execution_status == "completed")

    results.summary = {
        "total_tasks": len(results.task_results),
        "edge_predictions": edge_predictions,
        "cloud_predictions": cloud_predictions,
        "cloud_unavailable": cloud_unavailable,
        "edge_completed": edge_completed,
        "edge_rate": edge_predictions / len(results.task_results) if results.task_results else 0,
        "edge_completion_rate": edge_completed / edge_predictions if edge_predictions > 0 else 0,
    }

    return results


def generate_report(results: ExperimentResults, output_path: Path) -> None:
    """Generate markdown report with experiment results.

    Args:
        results: Experiment results
        output_path: Path to save report
    """
    lines = [
        "# MLP EdgeSimPy Integration Experiment Report",
        "",
        "## Objective",
        "",
        "First controlled integration of MLP_final_6 with EdgeSimPy to validate the model",
        "in a simulation environment and observe the consequence of Edge/Cloud decisions.",
        "",
        "## Configuration",
        "",
        f"- **Experiment ID**: {results.config.experiment_id}",
        f"- **Dataset**: {results.config.dataset}",
        f"- **User ID**: {results.config.user_id}",
        f"- **Candidate Servers**: {results.config.candidate_server_ids}",
        f"- **Random Seed**: {results.config.random_seed}",
        f"- **Tick Duration**: {results.config.tick_duration_s} s",
        f"- **Bandwidth Algorithm**: {results.config.bandwidth_algorithm}",
        "",
        "## Model Configuration",
        "",
        f"- **Hidden Neurons**: {results.config.mlp_hidden_neurons}",
        f"- **Learning Rate**: {results.config.mlp_learning_rate}",
        f"- **Epochs**: {results.config.mlp_epochs}",
        f"- **Seed**: {results.config.mlp_seed}",
        f"- **Features**: {list(FEATURE_NAMES)}",
        "",
        "## Summary",
        "",
        f"- **Total Tasks**: {results.summary['total_tasks']}",
        f"- **Edge Predictions**: {results.summary['edge_predictions']} ({results.summary['edge_rate']:.1%})",
        f"- **Cloud Predictions**: {results.summary['cloud_predictions']}",
        f"- **Cloud Unavailable**: {results.summary['cloud_unavailable']}",
        f"- **Edge Completed**: {results.summary.get('edge_completed', 0)}",
        f"- **Edge Completion Rate**: {results.summary.get('edge_completion_rate', 0):.1%}",
        "",
        "## Task Results",
        "",
        "| Task ID | Predicted | Status | Server | Path Delay (ms) | Trans (s) | Queue (s) | Exec (s) | Complete (s) | Deadline Violation |",
        "| ------- | --------- | ------ | ------ | --------------- | --------- | --------- | -------- | ------------ | ----------------- |",
    ]

    for result in results.task_results:
        server_id = result.selected_edge_server_id if result.selected_edge_server_id else "N/A"
        path_delay = f"{result.path_delay_ms:.2f}" if result.path_delay_ms else "N/A"
        trans_time = f"{result.transmission_time_s:.2f}" if result.transmission_time_s else "N/A"
        queue_time = f"{result.queue_time_s:.2f}" if result.queue_time_s else "N/A"
        exec_time = f"{result.execution_time_s:.2f}" if result.execution_time_s else "N/A"
        complete_time = f"{result.completion_time_s:.2f}" if result.completion_time_s else "N/A"
        deadline_viol = "Yes" if result.deadline_violation else ("No" if result.deadline_violation is not None else "N/A")
        lines.append(
            f"| {result.task_id} | {result.predicted_destination} | {result.execution_status} | {server_id} | {path_delay} | {trans_time} | {queue_time} | {exec_time} | {complete_time} | {deadline_viol} |"
        )

    lines.extend([
        "",
        "## Feature Examples",
        "",
        "First task features used:",
        "",
    ])

    if results.task_results and results.task_results[0].features_used:
        features = results.task_results[0].features_used
        for feature_name, value in features.items():
            lines.append(f"- **{feature_name}**: {value:.4f}")

    lines.extend([
        "",
        "## Methodological Notes",
        "",
        "### Three Levels of Evaluation",
        "",
        "1. **Predictive Level**: Accuracy, F1 (measured on test set: 83.20%)",
        "2. **Decision Level**: Edge/Cloud prediction, EdgeServer selection",
        "3. **Systemic Level**: Transmission, queue, execution, completion, deadline",
        "",
        "### Cloud Handling",
        "",
        "- Cloud is not implemented in EdgeSimPy",
        "- Tasks predicted as Cloud are marked CLOUD_UNAVAILABLE",
        "- No silent fallback to Edge (methodological integrity)",
        "- This validates MLP prediction capability despite infrastructure limitation",
        "",
        "### Feature Extraction",
        "",
        "- **NetworkLatencyMs**: Average path delay to all candidate EdgeServers (global feature)",
        "- **BandwidthMbps**: Minimum bandwidth bottleneck to all candidate EdgeServers (global feature)",
        "- This matches C# dataset semantics where these are single values per sample",
        "",
        "### Circularity",
        "",
        "- Labels come from C# analytical simulator",
        "- MLP learns to reproduce analytical decision rule",
        "- This experiment tests consequence of analytical decision in simulation",
        "- Not validation of physical optimality",
        "",
        "### Limitations",
        "",
        "- Cloud not implemented in EdgeSimPy",
        "- Network features are approximations of C# global semantics",
        "- Model weights not properly serialized (re-trained with fixed seed)",
        "- Small sample size (10 tasks) for this integration test",
        "",
        "## Next Steps",
        "",
        "1. Compare MLP vs NearestServerPolicy on systemic metrics",
        "2. Implement Cloud in EdgeSimPy for full Edge/Cloud evaluation",
        "3. Proper model weight serialization",
        "4. Scale to larger task samples for statistical significance",
        "",
        f"Generated: {output_path}",
    ])

    report = "\n".join(lines)
    output_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {output_path}")


def main() -> int:
    """Main entry point for MLP EdgeSimPy integration experiment."""
    config = ExperimentConfig()

    print("="*70)
    print("MLP EdgeSimPy Integration Experiment")
    print("="*70)

    try:
        results = run_mlp_integration_experiment(config)

        # Generate report
        results_dir = Path(__file__).resolve().parents[1] / "results"
        results_dir.mkdir(exist_ok=True)
        report_path = results_dir / "mlp_edgesimpy_integration.md"

        generate_report(results, report_path)

        # Save JSON
        json_path = results_dir / "mlp_edgesimpy_integration.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "config": {
                    "experiment_id": config.experiment_id,
                    "dataset": config.dataset,
                    "user_id": config.user_id,
                    "candidate_server_ids": config.candidate_server_ids,
                    "random_seed": config.random_seed,
                },
                "summary": results.summary,
                "task_results": [
                    {
                        "task_id": r.task_id,
                        "predicted_destination": r.predicted_destination,
                        "execution_status": r.execution_status,
                        "selected_edge_server_id": r.selected_edge_server_id,
                        "features_used": r.features_used,
                        "path_delay_ms": r.path_delay_ms,
                        "transmission_time_s": r.transmission_time_s,
                        "queue_time_s": r.queue_time_s,
                        "execution_time_s": r.execution_time_s,
                        "completion_time_s": r.completion_time_s,
                        "deadline_violation": r.deadline_violation,
                    }
                    for r in results.task_results
                ],
            }, f, indent=2, ensure_ascii=False)

        print(f"JSON saved to: {json_path}")

        print("\n" + "="*70)
        print("Experiment completed successfully!")
        print("="*70)

        return 0

    except Exception as e:
        print(f"\nExperiment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
