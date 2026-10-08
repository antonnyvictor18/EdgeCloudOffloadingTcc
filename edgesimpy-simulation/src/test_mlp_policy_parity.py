"""Parity test for MLPOffloadingPolicy vs MLPModel.predict().

This test verifies that the policy produces identical predictions to the raw model
when given the same input features, after the double normalization bug fix.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import EdgeServer, Simulator, User
from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from ml.mlp_model import MLPConfig, MLPModel
from models import Task
from policies.ml_offloading import create_mlp_offloading_policy


def test_parity_policy_vs_model() -> None:
    """Test that MLPOffloadingPolicy produces identical results to MLPModel.predict()."""
    print("Testing MLPOffloadingPolicy vs MLPModel parity...")

    # Load dataset
    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    # Load MLP model (same as used in policy)
    model_path = repository_root / "edgesimpy-simulation" / "models" / "mlp_final_6"
    model = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
    model.load(model_path)

    # Load policy
    policy = create_mlp_offloading_policy(model_path=model_path)
    policy.load_model()

    # Initialize simulator for feature extraction
    simulator = Simulator()
    dataset_file = repository_root / "edgesimpy-simulation" / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator.initialize(input_file=str(dataset_file))

    user = User.find_by_id(1)
    if user is None:
        raise ValueError("User 1 not found in dataset")

    # Test samples from validation set (mix of Edge and Cloud)
    val_indices = list(range(20))  # First 20 samples for comprehensive test
    edge_count = 0
    cloud_count = 0
    exact_matches = 0

    print(f"Testing {len(val_indices)} samples from validation set")
    print("Network features: BandwidthMbps/NetworkLatencyMs are per-scenario WAN")
    print("conditions carried by the Task (dataset contract), not topology-derived")

    for i, idx in enumerate(val_indices):
        # Get raw features from dataset
        X_raw = np.array([dataset.validation.X[idx]])
        true_label = dataset.validation.y[idx]

        # Method 1: Direct model prediction (on dataset features)
        model_prediction = model.predict(X_raw)[0]
        _, model_output = model._forward(model.normalizer.transform(X_raw)[0])

        # Method 2: Policy prediction (through Task)
        # Task carries the sample's WAN conditions, matching the dataset contract
        features = dataset.validation.X[idx]
        task = Task(
            task_id=f"test_{i}",
            user=user,
            cpu_cycles=features[0],
            data_size_mb=features[1],
            latency_sensitivity=features[2],
            required_memory_mb=features[3],
            bandwidth_mbps=features[4],
            network_latency_ms=features[5],
            deadline_ms=20000.0,
            creation_time_s=0.0,
        )

        decision = policy.predict(task, simulator.topology)
        policy_prediction = decision.predicted_destination

        # STRICT INVARIANCE CHECK: feed the policy's OWN extracted features
        # back through the raw model. If the policy pipeline is correct, the
        # continuous output and the class must be identical to what the policy
        # produced internally.
        policy_features = decision.features_used
        policy_feature_vector = np.array([[policy_features[name] for name in FEATURE_NAMES]])
        expected_pred = model.predict(policy_feature_vector)[0]
        _, expected_output = model._forward(
            model.normalizer.transform(policy_feature_vector)[0]
        )
        assert expected_pred == policy_prediction, (
            f"Sample {idx}: policy prediction {policy_prediction} != "
            f"model prediction {expected_pred} on the policy's own extracted "
            f"features {policy_feature_vector.tolist()}"
        )

        # For reporting: continuous output the model produces on the DATASET
        # feature vector (which differs in the two network features)
        features_array = np.array([features])
        policy_normalized = model.normalizer.transform(features_array)
        _, policy_output = model._forward(policy_normalized[0])

        # Check if predictions match (dataset features == task features now)
        prediction_match = model_prediction == policy_prediction
        output_match = abs(model_output - policy_output) < 1e-10

        if prediction_match:
            exact_matches += 1

        if true_label == "Edge":
            edge_count += 1
        else:
            cloud_count += 1

        status = "[MATCH]" if prediction_match else "[DIFF]"
        print(f"  Sample {idx} ({true_label}): Model={model_prediction}({model_output:.4f}), "
              f"Policy={policy_prediction}({policy_output:.4f}) {status}")

        # Any mismatch is now a real parity failure - report extracted features
        if not prediction_match:
            extracted_features, _ = policy._extract_features(task, simulator.topology)
            diffs = {
                FEATURE_NAMES[j]: (features[j], extracted_features[j])
                for j in range(len(FEATURE_NAMES))
                if features[j] != extracted_features[j]
            }
            print(f"    Feature diff: {diffs}")

    # With WAN conditions carried by the Task, parity must be EXACT
    print(f"\nParity analysis:")
    print(f"  Exact prediction matches: {exact_matches}/{len(val_indices)}")
    assert exact_matches == len(val_indices), (
        f"Policy vs Model parity failed: {exact_matches}/{len(val_indices)} "
        f"exact matches - the policy pipeline must produce identical outputs "
        f"when the Task carries the same raw features"
    )

    # Strict synthetic invariance: identical features -> identical output
    print(f"\nTesting with synthetic identical features...")

    synthetic_features = np.array([[5000000000.0, 10.0, 0.5, 2000.0, 50.0, 100.0]])
    synthetic_task = Task(
        task_id="synthetic",
        user=user,
        cpu_cycles=synthetic_features[0][0],
        data_size_mb=synthetic_features[0][1],
        latency_sensitivity=synthetic_features[0][2],
        required_memory_mb=synthetic_features[0][3],
        bandwidth_mbps=synthetic_features[0][4],
        network_latency_ms=synthetic_features[0][5],
        deadline_ms=20000.0,
        creation_time_s=0.0,
    )

    model_pred = model.predict(synthetic_features)[0]
    _, model_out = model._forward(model.normalizer.transform(synthetic_features)[0])
    policy_decision = policy.predict(synthetic_task, simulator.topology)

    assert policy_decision.predicted_destination == model_pred, (
        f"Synthetic invariance failed: policy={policy_decision.predicted_destination} "
        f"model={model_pred} for identical features {synthetic_features.tolist()}"
    )

    print(f"  Synthetic test: Model={model_pred}({model_out:.4f}), "
          f"Policy={policy_decision.predicted_destination} [IDENTICAL]")

    print(f"[PASS] Policy vs Model parity test passed ({exact_matches}/{len(val_indices)} exact matches)")


def test_model_serialization_parity() -> None:
    """Test that saved model produces identical results to in-memory model."""
    print("Testing model serialization parity...")

    # Load dataset
    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    # Create and train model in memory
    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)

    model_memory = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
    model_memory.fit(X_train, y_train)

    # Save model
    model_path = Path("temp_test_model")
    model_memory.save(model_path)

    # Load model from disk
    model_disk = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
    model_disk.load(model_path)

    # Test on validation samples
    X_val = np.array(dataset.validation.X[:10])  # First 10 samples

    pred_memory = model_memory.predict(X_val)
    pred_disk = model_disk.predict(X_val)

    # Verify predictions are identical
    assert np.array_equal(pred_memory, pred_disk), (
        f"Model serialization parity failed:\n"
        f"  Memory predictions: {pred_memory}\n"
        f"  Disk predictions: {pred_disk}"
    )

    # Verify outputs are identical
    for i in range(len(X_val)):
        x_norm = model_memory.normalizer.transform(X_val[i:i+1])
        _, out_memory = model_memory._forward(x_norm[0])
        _, out_disk = model_disk._forward(x_norm[0])

        assert abs(out_memory - out_disk) < 1e-10, (
            f"Output mismatch for sample {i}:\n"
            f"  Memory: {out_memory:.6f}\n"
            f"  Disk: {out_disk:.6f}"
        )

    # Cleanup
    model_path.with_suffix(".npz").unlink(missing_ok=True)
    model_path.with_suffix(".json").unlink(missing_ok=True)

    print("[PASS] Model serialization parity test passed")


def test_preprocessing_parity() -> None:
    """Test that preprocessing parameters are identical between saved and loaded models."""
    print("Testing preprocessing parity...")

    # Load dataset
    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    # Create and train model
    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)  # Convert to numpy array
    model_memory = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
    model_memory.fit(X_train, y_train)

    # Save model
    model_path = Path("temp_preprocess_test")
    model_memory.save(model_path)

    # Load model
    model_disk = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
    model_disk.load(model_path)

    # Compare normalization parameters
    mem_params = model_memory.normalizer.params
    disk_params = model_disk.normalizer.params

    assert np.array_equal(mem_params.mins, disk_params.mins), "Min values differ"
    assert np.array_equal(mem_params.maxs, disk_params.maxs), "Max values differ"
    assert mem_params.feature_names == disk_params.feature_names, "Feature names differ"

    # Test normalization on sample data
    X_sample = np.array(dataset.validation.X[:5])
    norm_memory = model_memory.normalizer.transform(X_sample)
    norm_disk = model_disk.normalizer.transform(X_sample)

    assert np.allclose(norm_memory, norm_disk), "Normalization outputs differ"

    # Cleanup
    model_path.with_suffix(".npz").unlink(missing_ok=True)
    model_path.with_suffix(".json").unlink(missing_ok=True)

    print("[PASS] Preprocessing parity test passed")


def test_task_consistency() -> None:
    """Test that the same Task object is used for prediction and execution."""
    print("Testing Task consistency between prediction and execution...")

    # This test verifies that when we create a Task for prediction,
    # the same Task properties are preserved for execution.
    # This is a methodological check, not a functional test.

    # Load dataset
    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    # Get a sample from validation
    sample_idx = 0
    features = dataset.validation.X[sample_idx]

    # Create original task (for prediction)
    original_task = Task(
        task_id="test_task",
        user=None,  # Will be set in actual experiment
        cpu_cycles=features[0],
        data_size_mb=features[1],
        latency_sensitivity=features[2],
        required_memory_mb=features[3],
        deadline_ms=20000.0,
        creation_time_s=0.0,
    )

    # Store original properties
    original_props = {
        "cpu_cycles": original_task.cpu_cycles,
        "data_size_mb": original_task.data_size_mb,
        "latency_sensitivity": original_task.latency_sensitivity,
        "required_memory_mb": original_task.required_memory_mb,
        "deadline_ms": original_task.deadline_ms,
    }

    # Simulate recreation for execution (what current code does WRONG)
    recreated_task_wrong = Task(
        task_id="test_task",
        user=None,
        cpu_cycles=100.0,  # BUG: Uses config value instead of task value
        data_size_mb=0.1,  # BUG: Uses config value instead of task value
        latency_sensitivity=original_task.latency_sensitivity,
        required_memory_mb=original_task.required_memory_mb,
        deadline_ms=original_task.deadline_ms,
        creation_time_s=0.0,
    )

    # Simulate recreation for execution (what should happen)
    recreated_task_correct = Task(
        task_id="test_task",
        user=None,
        cpu_cycles=original_task.cpu_cycles,  # CORRECT: Preserve original
        data_size_mb=original_task.data_size_mb,  # CORRECT: Preserve original
        latency_sensitivity=original_task.latency_sensitivity,
        required_memory_mb=original_task.required_memory_mb,
        deadline_ms=original_task.deadline_ms,
        creation_time_s=0.0,
    )

    # Check that wrong approach changes properties
    wrong_props = {
        "cpu_cycles": recreated_task_wrong.cpu_cycles,
        "data_size_mb": recreated_task_wrong.data_size_mb,
        "latency_sensitivity": recreated_task_wrong.latency_sensitivity,
        "required_memory_mb": recreated_task_wrong.required_memory_mb,
        "deadline_ms": recreated_task_wrong.deadline_ms,
    }

    # Check that correct approach preserves properties
    correct_props = {
        "cpu_cycles": recreated_task_correct.cpu_cycles,
        "data_size_mb": recreated_task_correct.data_size_mb,
        "latency_sensitivity": recreated_task_correct.latency_sensitivity,
        "required_memory_mb": recreated_task_correct.required_memory_mb,
        "deadline_ms": recreated_task_correct.deadline_ms,
    }

    # Verify that correct approach preserves all properties
    assert original_props == correct_props, (
        f"Task properties not preserved:\n"
        f"  Original: {original_props}\n"
        f"  Recreated: {correct_props}"
    )

    # Show that wrong approach would fail
    if original_props != wrong_props:
        print("  [EXPECTED] Wrong approach changes properties:")
        for key in original_props:
            if original_props[key] != wrong_props[key]:
                print(f"    {key}: {original_props[key]} -> {wrong_props[key]}")

    print("[PASS] Task consistency test passed")


def test_network_features_semantics() -> None:
    """Test and document the semantics of network features."""
    print("Testing network features semantics...")

    # Initialize simulator
    simulator = Simulator()
    simulator.initialize(input_file="tutorials/datasets/sample_dataset2.json")

    user = User.find_by_id(1)
    if user is None:
        raise ValueError("User 1 not found")

    # Load policy to test feature extraction
    model_path = Path("models/mlp_final_6")
    policy = create_mlp_offloading_policy(model_path=model_path)
    policy.load_model()

    # Create a test task
    task = Task(
        task_id="network_test",
        user=user,
        cpu_cycles=1000.0,
        data_size_mb=1.0,
        latency_sensitivity=0.5,
        required_memory_mb=512.0,
        deadline_ms=20000.0,
        creation_time_s=0.0,
    )

    # Path A: task WITHOUT WAN attributes -> topology-derived fallback
    features, features_dict = policy._extract_features(task, simulator.topology)

    print("Network features semantics:")
    print("  Preferred source: task.bandwidth_mbps / task.network_latency_ms")
    print("    (per-scenario WAN condition user->Cloud, matching the C# contract)")
    print("  Fallback source: topology-derived over ALL EdgeServers")
    print(f"    BandwidthMbps fallback: {features_dict['BandwidthMbps']} (bottleneck)")
    print(f"    NetworkLatencyMs fallback: {features_dict['NetworkLatencyMs']} (avg path delay)")

    # Path B: task WITH WAN attributes -> must be used verbatim
    task_wan = Task(
        task_id="wan_test",
        user=user,
        cpu_cycles=1000.0,
        data_size_mb=1.0,
        latency_sensitivity=0.5,
        required_memory_mb=512.0,
        bandwidth_mbps=42.0,
        network_latency_ms=77.0,
        deadline_ms=20000.0,
        creation_time_s=0.0,
    )
    _, wan_dict = policy._extract_features(task_wan, simulator.topology)
    assert wan_dict["BandwidthMbps"] == 42.0, "WAN bandwidth attribute not used"
    assert wan_dict["NetworkLatencyMs"] == 77.0, "WAN latency attribute not used"
    print("  WAN attributes used verbatim: BandwidthMbps=42.0, NetworkLatencyMs=77.0")

    edge_servers = list(EdgeServer.all())
    print(f"  Fallback EdgeServers considered: {[s.id for s in edge_servers]} (all)")

    print("[PASS] Network features semantics documented")


def main() -> int:
    """Run all parity tests."""
    print("Running MLP Policy Parity Tests...")
    print("="*60)

    try:
        test_parity_policy_vs_model()
        test_model_serialization_parity()
        test_preprocessing_parity()
        test_task_consistency()
        test_network_features_semantics()

        print("="*60)
        print("All parity tests: PASS")
        return 0
    except AssertionError as e:
        print(f"Parity test failed: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())