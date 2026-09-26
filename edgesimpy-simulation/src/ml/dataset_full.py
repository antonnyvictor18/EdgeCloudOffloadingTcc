"""Dataset loader that includes all features from the CSV (for feature set analysis)."""

from __future__ import annotations

import csv
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

# Full feature set from the CSV
FULL_FEATURE_NAMES = (
    "CpuCycles",
    "TaskSizeMB",
    "DeadlineMs",
    "LatencySensitivity",
    "RequiredMemoryMB",
    "EdgeCpuUsagePercent",
    "EdgeMemoryUsagePercent",
    "EdgeQueueSize",
    "BandwidthMbps",
    "NetworkLatencyMs",
    "CloudCpuUsagePercent",
    "CloudQueueSize",
)

VALID_LABELS = frozenset({"Edge", "Cloud"})


@dataclass(frozen=True)
class FullDatasetMetadata:
    """Metadata for full dataset with all features."""

    dataset_version: str
    source_path: str
    source_seed: int | None
    split_seed: int
    label_source: str
    feature_names: tuple[str, ...]
    sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "source_path": self.source_path,
            "source_seed": self.source_seed,
            "split_seed": self.split_seed,
            "label_source": self.label_source,
            "feature_names": list(self.feature_names),
            "sample_count": self.sample_count,
        }


@dataclass(frozen=True)
class FullSplitDataset:
    """Split dataset with all features."""

    X: tuple[tuple[float, ...], ...]
    y: tuple[str, ...]
    sample_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.X) != len(self.y) or len(self.X) != len(self.sample_ids):
            raise ValueError("X, y and sample_ids must have equal length")
        if any(len(row) != len(FULL_FEATURE_NAMES) for row in self.X):
            raise ValueError("every feature row must match FULL_FEATURE_NAMES")
        if any(label not in VALID_LABELS for label in self.y):
            raise ValueError("invalid label in split")


@dataclass(frozen=True)
class FullPreparedDataset:
    """Prepared dataset with all features."""

    all_data: FullSplitDataset
    train: FullSplitDataset
    validation: FullSplitDataset
    test: FullSplitDataset
    metadata: FullDatasetMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "sizes": {
                "all": len(self.all_data.y),
                "train": len(self.train.y),
                "validation": len(self.validation.y),
                "test": len(self.test.y),
            },
            "class_counts": {
                "all": dict(Counter(self.all_data.y)),
                "train": dict(Counter(self.train.y)),
                "validation": dict(Counter(self.validation.y)),
                "test": dict(Counter(self.test.y)),
            },
        }


def load_full_offloading_dataset(
    source_path: str | Path,
    *,
    source_seed: int | None = 42,
    split_seed: int = 43,
    dataset_version: str = "csharp-analytical-full-v1",
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
) -> FullPreparedDataset:
    """Load dataset with all features from CSV."""

    if not 0 < train_ratio < 1 or not 0 <= validation_ratio < 1:
        raise ValueError("split ratios must be between zero and one")
    if train_ratio + validation_ratio >= 1:
        raise ValueError("train plus validation ratios must be below one")

    path = Path(source_path)
    rows = _read_rows(path)
    all_data = _to_split(rows)
    train, validation, test = _stratified_split(
        all_data,
        train_ratio=train_ratio,
        validation_ratio=validation_ratio,
        seed=split_seed,
    )
    metadata = FullDatasetMetadata(
        dataset_version=dataset_version,
        source_path=str(path),
        source_seed=source_seed,
        split_seed=split_seed,
        label_source="analytical_simulator",
        feature_names=FULL_FEATURE_NAMES,
        sample_count=len(all_data.y),
    )
    return FullPreparedDataset(
        all_data=all_data,
        train=train,
        validation=validation,
        test=test,
        metadata=metadata,
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = {"BestDestination"} - columns
        if missing:
            raise ValueError(f"source CSV is missing columns: {sorted(missing)}")
        if not reader.fieldnames:
            raise ValueError("source CSV has no header")
        return list(reader)


def _to_split(rows: Iterable[dict[str, str]]) -> FullSplitDataset:
    features: list[tuple[float, ...]] = []
    labels: list[str] = []
    sample_ids: list[int] = []
    for sample_id, row in enumerate(rows):
        values = tuple(float(row[name]) for name in FULL_FEATURE_NAMES)
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"sample {sample_id} contains a non-finite feature")
        label = row["BestDestination"]
        if label not in VALID_LABELS:
            raise ValueError(f"sample {sample_id} has invalid label: {label!r}")
        features.append(values)
        labels.append(label)
        sample_ids.append(sample_id)
    if not features:
        raise ValueError("source dataset is empty")
    return FullSplitDataset(tuple(features), tuple(labels), tuple(sample_ids))


def _stratified_split(
    data: FullSplitDataset,
    *,
    train_ratio: float,
    validation_ratio: float,
    seed: int,
) -> tuple[FullSplitDataset, FullSplitDataset, FullSplitDataset]:
    randomizer = random.Random(seed)
    buckets: dict[str, list[int]] = {label: [] for label in VALID_LABELS}
    for index, label in enumerate(data.y):
        buckets[label].append(index)

    assignments: dict[str, list[int]] = {"train": [], "validation": [], "test": []}
    for indices in buckets.values():
        randomizer.shuffle(indices)
        train_end = round(len(indices) * train_ratio)
        validation_end = train_end + round(len(indices) * validation_ratio)
        assignments["train"].extend(indices[:train_end])
        assignments["validation"].extend(indices[train_end:validation_end])
        assignments["test"].extend(indices[validation_end:])

    for indices in assignments.values():
        randomizer.shuffle(indices)

    return tuple(_select(data, assignments[name]) for name in ("train", "validation", "test"))


def _select(data: FullSplitDataset, indices: Iterable[int]) -> FullSplitDataset:
    selected = list(indices)
    return FullSplitDataset(
        tuple(data.X[index] for index in selected),
        tuple(data.y[index] for index in selected),
        tuple(data.sample_ids[index] for index in selected),
    )
