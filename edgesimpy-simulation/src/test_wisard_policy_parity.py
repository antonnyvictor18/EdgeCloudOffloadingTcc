"""Parity test for WiSARDOffloadingPolicy vs WiSARDModel.predict().

This test verifies that the WiSARD policy produces identical predictions to
the raw model when given the same input features - same class of guarantee
as the MLP parity test (raw features in, model encodes internally, no
double preprocessing).

WiSARD has no continuous probability output; the pre-argmax evidence is the
per-class discriminator RAM hit counts, which this test also compares.

Contract notes:
- The Python WiSARD is trained on the frozen 6-feature contract
  (FEATURE_NAMES) fitted on dataset.train. It is NOT the 12-feature C#
  WisardStrategy, which uses server-state features that have no Task-level
  equivalent in EdgeSimPy and fixed FeatureRanges.
- The policy default is WISARD_FINAL_6 (thermometer encoding, 64 bits,
  16-bit addresses, bleaching) selected by experimento_tuning_wisard.py.
- There is no serialized WiSARD artifact; training in-session is
  deterministic (encoder fitted on train, RAM mapping seeded).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from edge_sim_py import Simulator, User
from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from ml.wisard_model import WISARD_FINAL_6
from models import Task
from policies.ml_offloading import (
    CloudUnavailableStatus,
    create_wisard_offloading_policy,
)


def _make_task(task_id: str, user: Any, features) -> Task:
    """Build a Task carrying the sample's dataset features incl. WAN attrs."""
    return Task(
        task_id=task_id,
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


def test_parity_policy_vs_model() -> None:
    """WiSARDOffloadingPolicy must produce identical results to WiSARDModel."""
    print("Testing WiSARDOffloadingPolicy vs WiSARDModel parity...")

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    # Train WiSARD in-session on dataset.train (no serialized artifact)
    policy = create_wisard_offloading_policy()
    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    policy.fit_model(X_train, y_train)
    model = policy.model

    # Initialize simulator for feature extraction
    simulator = Simulator()
    dataset_file = repository_root / "edgesimpy-simulation" / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator.initialize(input_file=str(dataset_file))

    user = User.find_by_id(1)
    if user is None:
        raise ValueError("User 1 not found in dataset")

    val_indices = list(range(20))
    exact_matches = 0
    score_matches = 0

    print(f"Testing {len(val_indices)} samples from validation set")
    print("Network features: WAN conditions carried by the Task (dataset contract)")

    for i, idx in enumerate(val_indices):
        X_raw = np.array([dataset.validation.X[idx]])
        true_label = dataset.validation.y[idx]

        # Method 1: direct model prediction on dataset features
        model_prediction = model.predict(X_raw)[0]
        model_scores = policy.scores(X_raw)

        # Method 2: policy prediction through Task carrying WAN attrs
        task = _make_task(f"test_{i}", user, dataset.validation.X[idx])
        decision = policy.predict(task, simulator.topology)
        policy_prediction = decision.predicted_destination
        policy_scores = policy.scores_for_task(task, simulator.topology)

        # STRICT INVARIANCE: feed the policy's OWN extracted features back
        # through the raw model - prediction and scores must be identical
        pf = decision.features_used
        policy_feature_vector = np.array([[pf[name] for name in FEATURE_NAMES]])
        expected_pred = model.predict(policy_feature_vector)[0]
        assert expected_pred == policy_prediction, (
            f"Sample {idx}: policy prediction {policy_prediction} != model "
            f"prediction {expected_pred} on the policy's own extracted "
            f"features {policy_feature_vector.tolist()}"
        )

        prediction_match = model_prediction == policy_prediction
        scores_match = model_scores == policy_scores
        if prediction_match:
            exact_matches += 1
        if scores_match:
            score_matches += 1

        status = "[MATCH]" if prediction_match else "[DIFF]"
        print(
            f"  Sample {idx} ({true_label}): Model={model_prediction}"
            f"{model_scores}, Policy={policy_prediction}{policy_scores} {status}"
        )

        if not prediction_match:
            from policies.ml_offloading import extract_task_features
            extracted, _ = extract_task_features(task, simulator.topology)
            diffs = {
                FEATURE_NAMES[j]: (dataset.validation.X[idx][j], extracted[j])
                for j in range(len(FEATURE_NAMES))
                if dataset.validation.X[idx][j] != extracted[j]
            }
            print(f"    Feature diff: {diffs}")

    print(f"\nParity analysis:")
    print(f"  Exact prediction matches: {exact_matches}/{len(val_indices)}")
    print(f"  Exact score matches: {score_matches}/{len(val_indices)}")
    assert exact_matches == len(val_indices), (
        f"WiSARD policy vs model parity failed: {exact_matches}/{len(val_indices)}"
    )
    assert score_matches == len(val_indices), (
        f"WiSARD score parity failed: {score_matches}/{len(val_indices)} - "
        f"the policy path must produce identical discriminator evidence"
    )

    # Synthetic invariance check
    print("\nTesting with synthetic identical features...")
    synthetic_features = np.array([[5000000000.0, 10.0, 0.5, 2000.0, 50.0, 100.0]])
    synthetic_task = _make_task("synthetic", user, synthetic_features[0])

    model_pred = model.predict(synthetic_features)[0]
    policy_decision = policy.predict(synthetic_task, simulator.topology)
    assert policy_decision.predicted_destination == model_pred, (
        f"Synthetic invariance failed: policy={policy_decision.predicted_destination} "
        f"model={model_pred}"
    )
    print(f"  Synthetic test: Model={model_pred}, "
          f"Policy={policy_decision.predicted_destination} [IDENTICAL]")

    print(f"[PASS] Policy vs Model parity test passed "
          f"({exact_matches}/{len(val_indices)} predictions, "
          f"{score_matches}/{len(val_indices)} scores)")


def test_training_determinism() -> None:
    """Same seed + same data must produce identical WiSARD predictions."""
    print("Testing WiSARD training determinism...")

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_val = np.array(dataset.validation.X[:50])

    policy_a = create_wisard_offloading_policy()
    policy_a.fit_model(X_train, y_train)
    policy_b = create_wisard_offloading_policy()
    policy_b.fit_model(X_train, y_train)

    pred_a = policy_a.model.predict(X_val)
    pred_b = policy_b.model.predict(X_val)
    assert np.array_equal(pred_a, pred_b), (
        "WiSARD is not deterministic: same seed + data gave different predictions"
    )

    # Encoder parameters must also be identical
    pa = policy_a.model._encoder.params.normalization
    pb = policy_b.model._encoder.params.normalization
    assert np.array_equal(pa.mins, pb.mins) and np.array_equal(pa.maxs, pb.maxs), (
        "Encoder normalization params differ between identical trainings"
    )

    print("[PASS] Training determinism test passed")


def test_encoder_preprocessing() -> None:
    """Verify WiSARD encoder contract: fitted on train only, correct bit width."""
    print("Testing WiSARD encoder preprocessing...")

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)

    policy = create_wisard_offloading_policy()
    policy.fit_model(X_train, y_train)

    params = policy.model._encoder.params
    cfg = policy.config.model
    assert cfg == WISARD_FINAL_6, "Policy default must be the frozen WISARD_FINAL_6 config"
    assert params.encoding == cfg.encoding
    assert params.bits_per_feature == cfg.bits_per_feature
    assert params.total_bits == len(FEATURE_NAMES) * cfg.bits_per_feature, (
        f"total_bits={params.total_bits}, expected "
        f"{len(FEATURE_NAMES) * cfg.bits_per_feature}"
    )

    # Normalization fitted on train split only
    assert np.array_equal(params.normalization.mins, X_train.min(axis=0))
    assert np.array_equal(params.normalization.maxs, X_train.max(axis=0))

    # Out-of-range inputs are clipped before quantization (no crash, valid bits)
    extreme = np.array([[
        X_train[:, 0].max() * 100, -5.0, 2.0, 99999.0, 0.0, 100000.0
    ]])
    encoded = policy.model._encoder.transform(extreme)
    assert encoded.shape == (1, params.total_bits)
    assert encoded.dtype == bool

    print(f"  Encoder: {params.encoding}, {params.bits_per_feature} bits/feature, "
          f"{params.total_bits} total bits, {policy.model.ram_count} RAMs, "
          f"bleaching={cfg.bleaching}, fitted on train split")
    print("[PASS] Encoder preprocessing test passed")


def test_decision_contract() -> None:
    """Cloud predictions must be CLOUD_UNAVAILABLE; Edge must be PENDING."""
    print("Testing WiSARD decision contract...")

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    policy = create_wisard_offloading_policy()
    policy.fit_model(np.array(dataset.train.X), np.array(dataset.train.y))

    simulator = Simulator()
    dataset_file = repository_root / "edgesimpy-simulation" / "tutorials" / "datasets" / "sample_dataset2.json"
    simulator.initialize(input_file=str(dataset_file))
    user = User.find_by_id(1)

    edge_seen = cloud_seen = 0
    for idx in range(len(dataset.validation.X)):
        task = _make_task(f"contract_{idx}", user, dataset.validation.X[idx])
        decision = policy.predict(task, simulator.topology)
        if decision.predicted_destination == "Cloud":
            assert decision.execution_status == CloudUnavailableStatus.CLOUD_UNAVAILABLE.value
            cloud_seen += 1
        elif decision.predicted_destination == "Edge":
            assert decision.execution_status == "PENDING"
            edge_seen += 1
        else:
            raise AssertionError(f"Unexpected prediction {decision.predicted_destination!r}")
        if edge_seen >= 10 and cloud_seen >= 10:
            break

    print(f"  Checked: {edge_seen} Edge (PENDING), {cloud_seen} Cloud (CLOUD_UNAVAILABLE)")
    assert cloud_seen > 0, "No Cloud predictions observed - contract not exercised"
    print("[PASS] Decision contract test passed")


def main() -> int:
    """Run all WiSARD parity tests."""
    print("Running WiSARD Policy Parity Tests...")
    print("=" * 60)

    try:
        test_parity_policy_vs_model()
        test_training_determinism()
        test_encoder_preprocessing()
        test_decision_contract()

        print("=" * 60)
        print("All WiSARD parity tests: PASS")
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
