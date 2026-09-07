"""Validation tests for the leakage-aware ML data contract."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.dataset import FEATURE_NAMES, FORBIDDEN_FEATURE_NAMES, load_offloading_dataset


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    source = repository_root / "Dataset" / "dataset.csv"
    first = load_offloading_dataset(source, source_seed=42, split_seed=43)
    second = load_offloading_dataset(source, source_seed=42, split_seed=43)

    assert len(FEATURE_NAMES) == 5
    assert first.metadata.label_source == "analytical_simulator"
    assert first.metadata.feature_names == FEATURE_NAMES
    assert not set(FEATURE_NAMES) & FORBIDDEN_FEATURE_NAMES
    assert all(label in {"Edge", "Cloud"} for label in first.all_data.y)
    assert len(first.all_data.X) == first.metadata.sample_count
    assert all(len(row) == len(FEATURE_NAMES) for row in first.all_data.X)
    assert first.to_dict() == second.to_dict()
    assert set(first.train.sample_ids).isdisjoint(first.validation.sample_ids)
    assert set(first.train.sample_ids).isdisjoint(first.test.sample_ids)
    assert set(first.validation.sample_ids).isdisjoint(first.test.sample_ids)
    assert set(first.train.sample_ids) | set(first.validation.sample_ids) | set(first.test.sample_ids) == set(first.all_data.sample_ids)
    assert all(value["min"] <= value["mean"] <= value["max"] for value in first.feature_statistics.values())

    print("ML dataset contract: PASS")
    print(f"samples={first.metadata.sample_count}")
    print(f"features={list(FEATURE_NAMES)}")
    print(f"train={len(first.train.y)} validation={len(first.validation.y)} test={len(first.test.y)}")
    print(f"labels={dict((label, first.all_data.y.count(label)) for label in sorted({*first.all_data.y}))}")
    print(f"label_source={first.metadata.label_source}")
    print(f"omitted_context={list(first.metadata.omitted_features[:2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
