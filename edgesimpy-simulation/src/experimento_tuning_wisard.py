"""Controlled hyperparameter study for WiSARD on the frozen 6-feature contract.

Protocol (model selection, not "tune until it looks good"):
- Train on dataset.train, select on dataset.validation ONLY. The test split
  is never touched.
- Primary selection metric: macro-F1 on validation. Accuracy is reported but
  NOT used for selection: with a 62/38 Edge/Cloud prior, accuracy rewards
  collapsing to the majority class - the exact failure mode being studied.
- Each configuration is trained with several RAM-mapping seeds; mean and
  standard deviation are reported. Selection uses the mean.
- Tie-break between configurations with equal mean macro-F1: fewer total
  input bits (simpler model), then fewer RAM cells written (memory).

Search space (design dimensions diagnosed on the default model):
- encoding: binary (C# WisardStrategy) vs thermometer (canonical WiSARD;
  adjacent quantization levels differ by one bit instead of up to `bits`).
- bits_per_feature: input resolution and, with ram_address_size, RAM count.
- ram_address_size: tuple size (generalization vs memorization).
- bleaching: tie resolution by raising the activation threshold.

Output: results/wisard_tuning.{json,md}
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from ml.metrics import compute_metrics
from ml.preprocessing import MAX_BINARY_BITS
from ml.wisard_model import WiSARDConfig, WiSARDModel


@dataclass(frozen=True)
class TuningGrid:
    encodings: tuple[str, ...] = ("binary", "thermometer")
    bits_per_feature: tuple[int, ...] = (4, 8, 16, 32, 64)
    ram_address_sizes: tuple[int, ...] = (2, 4, 8, 16)
    bleaching: tuple[bool, ...] = (False, True)
    seeds: tuple[int, ...] = (7, 11, 23, 42, 101)


@dataclass
class ConfigResult:
    encoding: str
    bits_per_feature: int
    ram_address_size: int
    bleaching: bool
    total_bits: int
    ram_count: int
    n_seeds: int
    macro_f1_mean: float
    macro_f1_std: float
    balanced_acc_mean: float
    balanced_acc_std: float
    accuracy_mean: float
    accuracy_std: float
    recall_cloud_mean: float
    recall_edge_mean: float
    edge_rate_mean: float
    tie_rate_mean: float
    stored_addresses_mean: float
    fit_predict_seconds_mean: float
    per_seed: list[dict[str, Any]]


def _evaluate_config(
    cfg_kwargs: dict[str, Any],
    seeds: tuple[int, ...],
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> ConfigResult:
    per_seed = []
    for seed in seeds:
        config = WiSARDConfig(seed=seed, **cfg_kwargs)
        model = WiSARDModel(config)
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        evidence = model.scores(X_val)
        elapsed = time.perf_counter() - t0

        y_pred = np.array([e["prediction"] for e in evidence])
        m = compute_metrics(y_val, y_pred)
        macro_f1 = (m.f1_edge + m.f1_cloud) / 2
        balanced_acc = (m.recall_edge + m.recall_cloud) / 2
        per_seed.append(
            {
                "seed": seed,
                "macro_f1": macro_f1,
                "balanced_accuracy": balanced_acc,
                "accuracy": m.accuracy,
                "recall_cloud": m.recall_cloud,
                "recall_edge": m.recall_edge,
                "precision_cloud": m.precision_cloud,
                "precision_edge": m.precision_edge,
                "edge_rate": float(np.mean(y_pred == "Edge")),
                "tie_rate": float(np.mean([e["tie"] for e in evidence])),
                "mean_threshold": float(np.mean([e["threshold"] for e in evidence])),
                "confusion_matrix": m.confusion_matrix,
                "stored_addresses": model.stored_addresses,
                "seconds": elapsed,
            }
        )
        ram_count = model.ram_count
        total_bits = model.encoder_params["total_bits"]

    def agg(key: str) -> tuple[float, float]:
        vals = np.array([s[key] for s in per_seed], dtype=float)
        return float(vals.mean()), float(vals.std(ddof=0))

    return ConfigResult(
        encoding=cfg_kwargs["encoding"],
        bits_per_feature=cfg_kwargs["bits_per_feature"],
        ram_address_size=cfg_kwargs["ram_address_size"],
        bleaching=cfg_kwargs["bleaching"],
        total_bits=total_bits,
        ram_count=ram_count,
        n_seeds=len(seeds),
        macro_f1_mean=agg("macro_f1")[0],
        macro_f1_std=agg("macro_f1")[1],
        balanced_acc_mean=agg("balanced_accuracy")[0],
        balanced_acc_std=agg("balanced_accuracy")[1],
        accuracy_mean=agg("accuracy")[0],
        accuracy_std=agg("accuracy")[1],
        recall_cloud_mean=agg("recall_cloud")[0],
        recall_edge_mean=agg("recall_edge")[0],
        edge_rate_mean=agg("edge_rate")[0],
        tie_rate_mean=agg("tie_rate")[0],
        stored_addresses_mean=agg("stored_addresses")[0],
        fit_predict_seconds_mean=agg("seconds")[0],
        per_seed=per_seed,
    )


def _selection_key(r: ConfigResult) -> tuple:
    # Higher macro-F1 first; then simpler (fewer bits); then less memory
    return (-round(r.macro_f1_mean, 6), r.total_bits, r.stored_addresses_mean)


def _marginal_effects(results: list[ConfigResult]) -> dict[str, dict[str, float]]:
    """Mean macro-F1 by level of each design dimension (averaged over the rest)."""
    effects: dict[str, dict[str, float]] = {}
    for dim in ("encoding", "bits_per_feature", "ram_address_size", "bleaching"):
        levels: dict[str, list[float]] = {}
        for r in results:
            levels.setdefault(str(getattr(r, dim)), []).append(r.macro_f1_mean)
        effects[dim] = {k: float(np.mean(v)) for k, v in sorted(levels.items(), key=lambda kv: kv[0])}
    return effects


def _write_markdown(
    path: Path,
    grid: TuningGrid,
    results: list[ConfigResult],
    baseline: ConfigResult,
    best: ConfigResult,
    majority_macro_f1: float,
    majority_acc: float,
    mlp_reference: dict[str, float] | None,
    effects: dict[str, dict[str, float]],
    n_train: int,
    n_val: int,
) -> None:
    def row(r: ConfigResult) -> str:
        return (
            f"| {r.encoding} | {r.bits_per_feature} | {r.ram_address_size} | "
            f"{'on' if r.bleaching else 'off'} | {r.ram_count} | "
            f"{r.macro_f1_mean:.4f} ± {r.macro_f1_std:.4f} | "
            f"{r.balanced_acc_mean:.4f} | {r.accuracy_mean:.4f} | "
            f"{r.recall_cloud_mean:.3f} | {r.edge_rate_mean:.3f} | {r.tie_rate_mean:.3f} |"
        )

    header = (
        "| encoding | bits | addr | bleach | RAMs | macro-F1 (mean ± sd) | bal. acc | accuracy | "
        "recall Cloud | Edge rate | tie rate |\n"
        "|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|"
    )

    lines = [
        "# WiSARD Hyperparameter Study (6-feature contract)",
        "",
        "## Protocol",
        "",
        f"- Train split: {n_train} samples; selection on validation split: {n_val} samples. **Test split untouched.**",
        f"- Features (frozen contract): {', '.join(FEATURE_NAMES)}",
        "- Primary selection metric: **macro-F1** (validation). Accuracy reported, not used for selection",
        "  (62/38 class prior makes accuracy reward majority collapse).",
        f"- Seeds per configuration (RAM mapping): {list(grid.seeds)} - mean ± sd reported; selection on the mean.",
        "- Tie-break between configurations: fewer total input bits, then fewer RAM cells written.",
        "- Encoder normalization fitted on train only; residual ties -> Edge (C# convention).",
        "",
        "## Search space",
        "",
        f"- encoding: {list(grid.encodings)}",
        f"- bits_per_feature: {list(grid.bits_per_feature)}",
        f"- ram_address_size: {list(grid.ram_address_sizes)}",
        f"- bleaching: {list(grid.bleaching)}",
        f"- configurations: {len(results)} x {len(grid.seeds)} seeds = {len(results) * len(grid.seeds)} trainings",
        "",
        "## Reference points (validation)",
        "",
        f"- Majority classifier (always Edge): accuracy {majority_acc:.4f}, macro-F1 {majority_macro_f1:.4f}",
    ]
    if mlp_reference:
        lines.append(
            f"- MLP_final_6 (frozen artifact): accuracy {mlp_reference['accuracy']:.4f}, "
            f"macro-F1 {mlp_reference['macro_f1']:.4f}, recall Cloud {mlp_reference['recall_cloud']:.3f}"
        )
    lines += [
        "",
        "## Baseline: C#-equivalent configuration",
        "",
        header,
        row(baseline),
        "",
        "## Selected configuration",
        "",
        header,
        row(best),
        "",
        f"Improvement over baseline: macro-F1 {baseline.macro_f1_mean:.4f} -> {best.macro_f1_mean:.4f} "
        f"(+{best.macro_f1_mean - baseline.macro_f1_mean:.4f}); "
        f"recall Cloud {baseline.recall_cloud_mean:.3f} -> {best.recall_cloud_mean:.3f}; "
        f"tie rate {baseline.tie_rate_mean:.3f} -> {best.tie_rate_mean:.3f}.",
        "",
        "Per-seed (selected):",
        "",
        "| seed | macro-F1 | bal. acc | accuracy | recall Cloud | Edge rate | tie rate | confusion [[Cloud,Edge],[Cloud,Edge]] |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for s in best.per_seed:
        lines.append(
            f"| {s['seed']} | {s['macro_f1']:.4f} | {s['balanced_accuracy']:.4f} | {s['accuracy']:.4f} | "
            f"{s['recall_cloud']:.3f} | {s['edge_rate']:.3f} | {s['tie_rate']:.3f} | {s['confusion_matrix']} |"
        )

    lines += ["", "## Marginal effects (mean macro-F1 by level, averaged over other dimensions)", ""]
    for dim, levels in effects.items():
        lines.append(f"- **{dim}**: " + ", ".join(f"{k}={v:.4f}" for k, v in levels.items()))

    lines += ["", "## Top 15 configurations", "", header]
    for r in sorted(results, key=_selection_key)[:15]:
        lines.append(row(r))

    lines += ["", "## All configurations", "", header]
    for r in sorted(results, key=_selection_key):
        lines.append(row(r))

    lines += [
        "",
        "## Notes",
        "",
        "- Confusion matrix rows/cols follow sorted labels: [Cloud, Edge].",
        "- `tie rate` = fraction of validation samples whose final decision was a residual tie resolved to Edge.",
        "- `RAMs` = ceil(total_bits / ram_address_size) per discriminator.",
        "- Selection was performed once, on validation, before any test-set or EdgeSimPy evaluation.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    dataset = load_offloading_dataset(
        repository_root / "Dataset" / "dataset.csv", source_seed=42, split_seed=43
    )
    X_train, y_train = np.array(dataset.train.X), np.array(dataset.train.y)
    X_val, y_val = np.array(dataset.validation.X), np.array(dataset.validation.y)

    grid = TuningGrid()
    combos = [
        c for c in itertools.product(grid.encodings, grid.bits_per_feature, grid.ram_address_sizes, grid.bleaching)
        # binary levels 2^bits-1 must fit int64; thermometer has no such limit
        if not (c[0] == "binary" and c[1] > MAX_BINARY_BITS)
    ]
    print(f"WiSARD tuning: {len(combos)} configurations x {len(grid.seeds)} seeds")
    print(f"train={len(y_train)} validation={len(y_val)} (test untouched)")

    results: list[ConfigResult] = []
    for i, (enc, bits, addr, bleach) in enumerate(combos, 1):
        kwargs = {"encoding": enc, "bits_per_feature": bits, "ram_address_size": addr, "bleaching": bleach}
        r = _evaluate_config(kwargs, grid.seeds, X_train, y_train, X_val, y_val)
        results.append(r)
        print(
            f"[{i:3d}/{len(combos)}] {enc:11s} bits={bits:2d} addr={addr:2d} bleach={int(bleach)} "
            f"RAMs={r.ram_count:3d} | macroF1={r.macro_f1_mean:.4f}±{r.macro_f1_std:.4f} "
            f"acc={r.accuracy_mean:.4f} rCloud={r.recall_cloud_mean:.3f} "
            f"edge={r.edge_rate_mean:.3f} tie={r.tie_rate_mean:.3f} ({r.fit_predict_seconds_mean:.2f}s)",
            flush=True,
        )

    baseline = next(
        r for r in results
        if r.encoding == "binary" and r.bits_per_feature == 4 and r.ram_address_size == 8 and not r.bleaching
    )
    best = sorted(results, key=_selection_key)[0]

    # Reference points on validation
    majority_pred = np.full(len(y_val), "Edge")
    mm = compute_metrics(y_val, majority_pred)
    majority_macro_f1 = (mm.f1_edge + mm.f1_cloud) / 2

    mlp_reference = None
    try:
        from ml.mlp_model import MLPConfig, MLPModel
        mlp = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
        mlp.load(repository_root / "edgesimpy-simulation" / "models" / "mlp_final_6")
        pm = compute_metrics(y_val, mlp.predict(X_val))
        mlp_reference = {
            "accuracy": pm.accuracy,
            "macro_f1": (pm.f1_edge + pm.f1_cloud) / 2,
            "recall_cloud": pm.recall_cloud,
        }
    except Exception as e:  # reference only; never blocks the study
        print(f"MLP reference unavailable: {e}")

    effects = _marginal_effects(results)

    results_dir = repository_root / "edgesimpy-simulation" / "results"
    results_dir.mkdir(exist_ok=True)
    payload = {
        "protocol": {
            "selection_split": "validation",
            "test_split_touched": False,
            "primary_metric": "macro_f1",
            "seeds": list(grid.seeds),
            "feature_names": list(FEATURE_NAMES),
            "n_train": int(len(y_train)),
            "n_validation": int(len(y_val)),
        },
        "grid": asdict(grid),
        "reference": {
            "majority": {"accuracy": mm.accuracy, "macro_f1": majority_macro_f1},
            "mlp_final_6": mlp_reference,
        },
        "baseline_csharp_equivalent": asdict(baseline),
        "selected": asdict(best),
        "marginal_effects_macro_f1": effects,
        "results": [asdict(r) for r in sorted(results, key=_selection_key)],
    }
    (results_dir / "wisard_tuning.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_markdown(
        results_dir / "wisard_tuning.md", grid, results, baseline, best,
        majority_macro_f1, mm.accuracy, mlp_reference, effects, len(y_train), len(y_val),
    )

    print("\n" + "=" * 70)
    print("Baseline (C#-equivalent):", f"macroF1={baseline.macro_f1_mean:.4f} acc={baseline.accuracy_mean:.4f}")
    print(
        "Selected:",
        f"encoding={best.encoding} bits={best.bits_per_feature} addr={best.ram_address_size} "
        f"bleaching={best.bleaching} | macroF1={best.macro_f1_mean:.4f}±{best.macro_f1_std:.4f} "
        f"acc={best.accuracy_mean:.4f} rCloud={best.recall_cloud_mean:.3f}",
    )
    if mlp_reference:
        print("MLP_final_6 reference:", f"macroF1={mlp_reference['macro_f1']:.4f} acc={mlp_reference['accuracy']:.4f}")
    print(f"Reports: {results_dir / 'wisard_tuning.md'} / .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
