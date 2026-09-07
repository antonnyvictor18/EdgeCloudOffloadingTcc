"""Reproducible, leakage-aware preparation of the C# offloading dataset."""

from __future__ import annotations

import csv
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

# These are the only fields currently guaranteed by both OffloadingSample and Task.
FEATURE_NAMES = (
    "CpuCycles",
    "TaskSizeMB",
    "DeadlineMs",
    "LatencySensitivity",
    "RequiredMemoryMB",
)

# These are valid future context extensions, but absent from the current CSV contract.
EDGE_SIMPY_CONTEXT_FEATURES = (
    "path_delay_ms",
    "admitted_task_count",
)

FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "ExecutionTimeEdge",
        "ExecutionTimeCloud",
        "TotalResponseTimeEdge",
        "TotalResponseTimeCloud",
        "BestDestination",
        "completion_time",
        "completion_time_s",
        "queue_time",
        "queue_time_s",
        "deadline_violation",
    }
)
VALID_LABELS = frozenset({"Edge", "Cloud"})
REQUIRED_SOURCE_COLUMNS = frozenset((*FEATURE_NAMES, "BestDestination"))


@dataclass(frozen=True)
class DatasetMetadata:
    """Traceability information for one prepared dataset."""

    dataset_version: str
    source_path: str
    source_seed: int | None
    split_seed: int
    label_source: str
    feature_names: tuple[str, ...]
    omitted_features: tuple[str, ...]
    sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "source_path": self.source_path,
            "source_seed": self.source_seed,
            "split_seed": self.split_seed,
            "label_source": self.label_source,
            "feature_names": list(self.feature_names),
            "omitted_features": list(self.omitted_features),
            "sample_count": self.sample_count,
        }


@dataclass(frozen=True)
class SplitDataset:
    """One reproducible split containing features, labels and sample IDs."""

    X: tuple[tuple[float, ...], ...]
    y: tuple[str, ...]
    sample_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.X) != len(self.y) or len(self.X) != len(self.sample_ids):
            raise ValueError("X, y and sample_ids must have equal length")
        if any(len(row) != len(FEATURE_NAMES) for row in self.X):
            raise ValueError("every feature row must match FEATURE_NAMES")
        if any(label not in VALID_LABELS for label in self.y):
            raise ValueError("invalid label in split")


@dataclass(frozen=True)
class PreparedDataset:
    """Prepared X/y data with deterministic splits and audit metadata."""

    all_data: SplitDataset
    train: SplitDataset
    validation: SplitDataset
    test: SplitDataset
    metadata: DatasetMetadata
    feature_statistics: dict[str, dict[str, float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "feature_statistics": self.feature_statistics,
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


def load_offloading_dataset(
    source_path: str | Path,
    *,
    source_seed: int | None = 42,
    split_seed: int = 43,
    dataset_version: str = "csharp-analytical-v1",
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
) -> PreparedDataset:
    """Load the current C# CSV and create reproducible stratified splits.

    The current CSV has no scenario/group identifier. Its generator creates
    independent random samples, so row-level stratification is the documented
    split strategy for this version. Future grouped data must provide a group
    identifier before using this loader unchanged.
    """
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
    metadata = DatasetMetadata(
        dataset_version=dataset_version,
        source_path=str(path),
        source_seed=source_seed,
        split_seed=split_seed,
        label_source="analytical_simulator",
        feature_names=FEATURE_NAMES,
        omitted_features=tuple(sorted((*EDGE_SIMPY_CONTEXT_FEATURES, *FORBIDDEN_FEATURE_NAMES))),
        sample_count=len(all_data.y),
    )
    return PreparedDataset(
        all_data=all_data,
        train=train,
        validation=validation,
        test=test,
        metadata=metadata,
        feature_statistics=_feature_statistics(all_data.X),
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_SOURCE_COLUMNS - columns
        if missing:
            raise ValueError(f"source CSV is missing columns: {sorted(missing)}")
        forbidden = columns & FORBIDDEN_FEATURE_NAMES
        # Result columns are allowed in the source file, but never copied into X.
        if not reader.fieldnames:
            raise ValueError("source CSV has no header")
        return list(reader)


def _to_split(rows: Iterable[dict[str, str]]) -> SplitDataset:
    features: list[tuple[float, ...]] = []
    labels: list[str] = []
    sample_ids: list[int] = []
    for sample_id, row in enumerate(rows):
        values = tuple(float(row[name]) for name in FEATURE_NAMES)
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
    return SplitDataset(tuple(features), tuple(labels), tuple(sample_ids))


def _stratified_split(
    data: SplitDataset,
    *,
    train_ratio: float,
    validation_ratio: float,
    seed: int,
) -> tuple[SplitDataset, SplitDataset, SplitDataset]:
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

    return tuple(_select(data, assignments[name]) for name in ("train", "validation", "test"))  # type: ignore[return-value]


def _select(data: SplitDataset, indices: Iterable[int]) -> SplitDataset:
    selected = list(indices)
    return SplitDataset(
        tuple(data.X[index] for index in selected),
        tuple(data.y[index] for index in selected),
        tuple(data.sample_ids[index] for index in selected),
    )


def _feature_statistics(rows: tuple[tuple[float, ...], ...]) -> dict[str, dict[str, float]]:
    return {
        name: {
            "min": min(row[index] for row in rows),
            "max": max(row[index] for row in rows),
            "mean": mean(row[index] for row in rows),
        }
        for index, name in enumerate(FEATURE_NAMES)
    }
