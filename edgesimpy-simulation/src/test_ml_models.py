"""Validation tests for the ML model pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.baseline import MajorityClassifier
from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from ml.metrics import compute_metrics
from ml.mlp_model import MLPConfig, MLPModel
from ml.preprocessing import MinMaxNormalizer, WiSARDEncoder
from ml.wisard_model import WiSARDConfig, WiSARDModel


def test_dataset_loading() -> None:
    """Test that dataset loads correctly."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    assert len(dataset.all_data.X) == dataset.metadata.sample_count
    assert len(dataset.train.X) + len(dataset.validation.X) + len(dataset.test.X) == len(dataset.all_data.X)
    assert all(len(row) == len(FEATURE_NAMES) for row in dataset.all_data.X)
    print("[PASS] Dataset loading test passed")


def test_preprocessing() -> None:
    """Test preprocessing without leakage."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    # Test MinMaxNormalizer
    normalizer = MinMaxNormalizer()
    X_train = np.array(dataset.train.X)
    X_test = np.array(dataset.test.X)

    normalizer.fit(X_train)
    X_train_norm = normalizer.transform(X_train)
    X_test_norm = normalizer.transform(X_test)

    # Check normalization ranges
    assert np.all(X_train_norm >= 0) and np.all(X_train_norm <= 1)
    assert np.all(X_test_norm >= 0) and np.all(X_test_norm <= 1)

    # Test WiSARDEncoder
    encoder = WiSARDEncoder(bits_per_feature=4)
    encoder.fit(X_train)
    X_train_encoded = encoder.transform(X_train)
    X_test_encoded = encoder.transform(X_test)

    # Check encoding
    assert X_train_encoded.dtype == bool
    assert X_test_encoded.dtype == bool
    assert X_train_encoded.shape[1] == len(FEATURE_NAMES) * 4

    print("[PASS] Preprocessing test passed")


def test_wisard_model() -> None:
    """Test WiSARD model training and prediction."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_test = np.array(dataset.test.X)

    model = WiSARDModel(WiSARDConfig())
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    assert len(predictions) == len(X_test)
    assert all(p in {"Edge", "Cloud"} for p in predictions)
    assert model.config.seed == 7

    print("[PASS] WiSARD model test passed")


def test_mlp_model() -> None:
    """Test MLP model training and prediction."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_test = np.array(dataset.test.X)

    model = MLPModel(MLPConfig())
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    assert len(predictions) == len(X_test)
    assert all(p in {"Edge", "Cloud"} for p in predictions)
    assert model.config.seed == 11

    print("[PASS] MLP model test passed")


def test_majority_classifier() -> None:
    """Test majority classifier baseline."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_test = np.array(dataset.test.X)

    model = MajorityClassifier()
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    assert len(predictions) == len(X_test)
    assert all(p == model.majority_class for p in predictions)
    assert model.majority_class in {"Edge", "Cloud"}

    print("[PASS] Majority classifier test passed")


def test_metrics() -> None:
    """Test metrics calculation."""
    y_true = np.array(["Edge", "Edge", "Cloud", "Cloud", "Edge"])
    y_pred = np.array(["Edge", "Cloud", "Cloud", "Cloud", "Edge"])

    metrics = compute_metrics(y_true, y_pred)

    assert 0 <= metrics.accuracy <= 1
    assert 0 <= metrics.precision_edge <= 1
    assert 0 <= metrics.recall_edge <= 1
    assert 0 <= metrics.f1_edge <= 1
    assert 0 <= metrics.precision_cloud <= 1
    assert 0 <= metrics.recall_cloud <= 1
    assert 0 <= metrics.f1_cloud <= 1
    assert len(metrics.confusion_matrix) == 2
    assert all(len(row) == 2 for row in metrics.confusion_matrix)

    print("[PASS] Metrics test passed")


def test_reproducibility() -> None:
    """Test that same seed produces same results."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_test = np.array(dataset.test.X)

    # Test WiSARD reproducibility
    config1 = WiSARDConfig(seed=7)
    config2 = WiSARDConfig(seed=7)

    model1 = WiSARDModel(config1)
    model2 = WiSARDModel(config2)

    model1.fit(X_train, y_train)
    model2.fit(X_train, y_train)

    pred1 = model1.predict(X_test)
    pred2 = model2.predict(X_test)

    assert np.array_equal(pred1, pred2)

    # Test MLP reproducibility
    config1 = MLPConfig(seed=11)
    config2 = MLPConfig(seed=11)

    model1 = MLPModel(config1)
    model2 = MLPModel(config2)

    model1.fit(X_train, y_train)
    model2.fit(X_train, y_train)

    pred1 = model1.predict(X_test)
    pred2 = model2.predict(X_test)

    assert np.array_equal(pred1, pred2)

    print("[PASS] Reproducibility test passed")


def test_test_set_untouched() -> None:
    """Test that test set is not used during training."""
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"

    dataset = load_offloading_dataset(source, source_seed=42, split_seed=43)

    # Ensure test set is disjoint from train and validation
    train_ids = set(dataset.train.sample_ids)
    val_ids = set(dataset.validation.sample_ids)
    test_ids = set(dataset.test.sample_ids)

    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)
    assert train_ids.isdisjoint(val_ids)

    print("[PASS] Test set untouched test passed")


def main() -> int:
    """Run all ML pipeline tests."""
    print("Running ML pipeline tests...")
    print("="*60)

    try:
        test_dataset_loading()
        test_preprocessing()
        test_wisard_model()
        test_mlp_model()
        test_majority_classifier()
        test_metrics()
        test_reproducibility()
        test_test_set_untouched()

        print("="*60)
        print("All ML pipeline tests: PASS")
        return 0
    except AssertionError as e:
        print(f"Test failed: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
