"""Final, single-shot evaluation of the frozen models on the untouched test split.

This script is meant to be run ONCE after model selection is closed:
- MLP_final_6: frozen artifact (models/mlp_final_6.{npz,json}), selected on
  validation in earlier phases.
- WISARD_FINAL_6: frozen configuration selected by experimento_tuning_wisard.py
  (validation-only). Trained on dataset.train only, exactly as during
  selection (no refit on train+validation, to stay consistent with the MLP).

Reported on dataset.test (never used before this script):
- accuracy, per-class precision/recall/F1, macro-F1, balanced accuracy,
  confusion matrix, with 95% bootstrap confidence intervals;
- paired McNemar test MLP vs WiSARD (same samples -> paired comparison);
- validation -> test shift, to detect selection optimism;
- parity closure: policy.predict(Task) == model.predict(X_raw) on ALL test
  samples (same pipeline the EdgeSimPy experiments use);
- WiSARD sensitivity to the RAM-mapping seed (the frozen model is seed 7).

Output: results/final_test_evaluation.{json,md}
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from ml.dataset import FEATURE_NAMES, load_offloading_dataset
from ml.metrics import compute_metrics
from ml.mlp_model import MLPConfig, MLPModel
from ml.wisard_model import WISARD_FINAL_6, WiSARDConfig, WiSARDModel

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 2026


@dataclass
class ModelEval:
    name: str
    split: str
    n: int
    accuracy: float
    macro_f1: float
    balanced_accuracy: float
    precision_edge: float
    recall_edge: float
    f1_edge: float
    precision_cloud: float
    recall_cloud: float
    f1_cloud: float
    edge_rate: float
    confusion_matrix: list[list[int]]  # rows/cols sorted labels [Cloud, Edge]
    ci95_accuracy: tuple[float, float] | None = None
    ci95_macro_f1: tuple[float, float] | None = None
    ci95_balanced_accuracy: tuple[float, float] | None = None


def _summary(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    m = compute_metrics(y_true, y_pred)
    return m.accuracy, (m.f1_edge + m.f1_cloud) / 2, (m.recall_edge + m.recall_cloud) / 2


def _evaluate(name: str, split: str, y_true: np.ndarray, y_pred: np.ndarray, bootstrap: bool) -> ModelEval:
    m = compute_metrics(y_true, y_pred)
    acc, mf1, bacc = _summary(y_true, y_pred)
    ev = ModelEval(
        name=name, split=split, n=len(y_true),
        accuracy=acc, macro_f1=mf1, balanced_accuracy=bacc,
        precision_edge=m.precision_edge, recall_edge=m.recall_edge, f1_edge=m.f1_edge,
        precision_cloud=m.precision_cloud, recall_cloud=m.recall_cloud, f1_cloud=m.f1_cloud,
        edge_rate=float(np.mean(y_pred == "Edge")),
        confusion_matrix=m.confusion_matrix,
    )
    if bootstrap:
        rng = np.random.RandomState(BOOTSTRAP_SEED)
        n = len(y_true)
        stats = np.empty((BOOTSTRAP_RESAMPLES, 3))
        for b in range(BOOTSTRAP_RESAMPLES):
            idx = rng.randint(0, n, n)
            stats[b] = _summary(y_true[idx], y_pred[idx])
        lo, hi = np.percentile(stats, [2.5, 97.5], axis=0)
        ev.ci95_accuracy = (float(lo[0]), float(hi[0]))
        ev.ci95_macro_f1 = (float(lo[1]), float(hi[1]))
        ev.ci95_balanced_accuracy = (float(lo[2]), float(hi[2]))
    return ev


def _mcnemar(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict[str, Any]:
    """Exact McNemar test on discordant pairs (A right/B wrong vs A wrong/B right)."""
    a_ok, b_ok = pred_a == y_true, pred_b == y_true
    n01 = int(np.sum(a_ok & ~b_ok))  # A correct, B wrong
    n10 = int(np.sum(~a_ok & b_ok))  # A wrong, B correct
    p = binomtest(n01, n01 + n10, 0.5).pvalue if (n01 + n10) > 0 else 1.0
    return {
        "a_correct_b_wrong": n01,
        "a_wrong_b_correct": n10,
        "both_correct": int(np.sum(a_ok & b_ok)),
        "both_wrong": int(np.sum(~a_ok & ~b_ok)),
        "p_value_exact": float(p),
        "accuracy_difference_a_minus_b": float(a_ok.mean() - b_ok.mean()),
    }


def _parity_on_test(model_name: str, model_predict, X_test: np.ndarray, test_tasks_predict) -> dict[str, Any]:
    direct = np.asarray(model_predict(X_test))
    via_policy = np.asarray(test_tasks_predict())
    mismatches = int(np.sum(direct != via_policy))
    return {"model": model_name, "n": int(len(direct)), "mismatches": mismatches, "exact": mismatches == 0}


def _fmt_ci(ci: tuple[float, float] | None) -> str:
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "-"


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    t = payload["test"]
    v = payload["validation"]
    mc = payload["mcnemar_mlp_vs_wisard"]
    lines = [
        "# Final Test-Set Evaluation (frozen models)",
        "",
        "## Protocol",
        "",
        f"- Test split: {payload['n_test']} samples, used **for the first time** in this evaluation.",
        f"- Features (frozen contract): {', '.join(FEATURE_NAMES)}",
        "- MLP_final_6: frozen artifact `models/mlp_final_6` (18 hidden, lr 0.04, 35 epochs, seed 11).",
        f"- WISARD_FINAL_6: {payload['wisard_config']} - trained on dataset.train only, as during selection.",
        f"- 95% CIs: percentile bootstrap, {BOOTSTRAP_RESAMPLES} resamples, seed {BOOTSTRAP_SEED}.",
        "- MLP vs WiSARD: exact McNemar test on discordant pairs (paired, same samples).",
        "- Confusion matrix rows/cols follow sorted labels: [Cloud, Edge].",
        "",
        "## Test-set results",
        "",
        "| Model | accuracy [95% CI] | macro-F1 [95% CI] | bal. acc [95% CI] | P/R/F1 Edge | P/R/F1 Cloud | Edge rate | CM [Cloud,Edge] |",
        "|---|---|---|---|---|---|---:|---|",
    ]
    for ev in t:
        lines.append(
            f"| {ev['name']} | {ev['accuracy']:.4f} {_fmt_ci(ev['ci95_accuracy'])} | "
            f"{ev['macro_f1']:.4f} {_fmt_ci(ev['ci95_macro_f1'])} | "
            f"{ev['balanced_accuracy']:.4f} {_fmt_ci(ev['ci95_balanced_accuracy'])} | "
            f"{ev['precision_edge']:.3f}/{ev['recall_edge']:.3f}/{ev['f1_edge']:.3f} | "
            f"{ev['precision_cloud']:.3f}/{ev['recall_cloud']:.3f}/{ev['f1_cloud']:.3f} | "
            f"{ev['edge_rate']:.3f} | {ev['confusion_matrix']} |"
        )
    lines += [
        "",
        "## Paired comparison: MLP vs WiSARD (McNemar, test set)",
        "",
        f"- MLP correct & WiSARD wrong: {mc['a_correct_b_wrong']}",
        f"- MLP wrong & WiSARD correct: {mc['a_wrong_b_correct']}",
        f"- both correct: {mc['both_correct']}; both wrong: {mc['both_wrong']}",
        f"- accuracy difference (MLP - WiSARD): {mc['accuracy_difference_a_minus_b']:+.4f}",
        f"- exact p-value: {mc['p_value_exact']:.2e}",
        "",
        "## Validation -> test shift (selection optimism check)",
        "",
        "| Model | split | accuracy | macro-F1 | bal. acc |",
        "|---|---|---:|---:|---:|",
    ]
    for ev in v + t:
        lines.append(f"| {ev['name']} | {ev['split']} | {ev['accuracy']:.4f} | {ev['macro_f1']:.4f} | {ev['balanced_accuracy']:.4f} |")

    lines += ["", "## Parity closure on the full test set (policy(Task) == model(X_raw))", ""]
    for p in payload["parity"]:
        lines.append(f"- {p['model']}: {p['n']} samples, {p['mismatches']} mismatches -> {'EXACT' if p['exact'] else 'FAILED'}")

    lines += ["", "## WiSARD sensitivity to RAM-mapping seed (test set; frozen model is seed 7)", "",
              "| seed | accuracy | macro-F1 | bal. acc | Edge rate |", "|---:|---:|---:|---:|---:|"]
    for s in payload["wisard_seed_sensitivity"]["per_seed"]:
        lines.append(f"| {s['seed']} | {s['accuracy']:.4f} | {s['macro_f1']:.4f} | {s['balanced_accuracy']:.4f} | {s['edge_rate']:.3f} |")
    ss = payload["wisard_seed_sensitivity"]
    lines.append(f"\nmacro-F1 across seeds: {ss['macro_f1_mean']:.4f} ± {ss['macro_f1_std']:.4f}")

    lines += [
        "",
        "## Notes",
        "",
        "- These are predictive (classifier-level) results against the analytical BestDestination label.",
        "  They do not measure offloading quality; see the EdgeSimPy systemic experiments for that level.",
        "- The analytical label is produced by the C# formula; agreement with it is reproduction of that",
        "  formula, not evidence of physical optimality (documented circularity).",
        "- This evaluation must not be used to select or tune models; selection is closed.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    dataset = load_offloading_dataset(repository_root / "Dataset" / "dataset.csv", source_seed=42, split_seed=43)
    X_train, y_train = np.array(dataset.train.X), np.array(dataset.train.y)
    X_val, y_val = np.array(dataset.validation.X), np.array(dataset.validation.y)
    X_test, y_test = np.array(dataset.test.X), np.array(dataset.test.y)

    assert set(dataset.test.sample_ids).isdisjoint(dataset.train.sample_ids)
    assert set(dataset.test.sample_ids).isdisjoint(dataset.validation.sample_ids)
    print(f"train={len(y_train)} validation={len(y_val)} test={len(y_test)} (first use of test)")

    # --- Frozen models ---
    mlp = MLPModel(MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11))
    mlp.load(repository_root / "edgesimpy-simulation" / "models" / "mlp_final_6")

    wisard = WiSARDModel(WISARD_FINAL_6)
    wisard.fit(X_train, y_train)

    majority = np.full(len(y_test), "Edge")

    pred_mlp_test, pred_wis_test = mlp.predict(X_test), wisard.predict(X_test)
    pred_mlp_val, pred_wis_val = mlp.predict(X_val), wisard.predict(X_val)

    print("Evaluating on test (with bootstrap CIs)...")
    test_evals = [
        _evaluate("MLP_final_6", "test", y_test, pred_mlp_test, bootstrap=True),
        _evaluate("WISARD_FINAL_6", "test", y_test, pred_wis_test, bootstrap=True),
        _evaluate("Majority(Edge)", "test", y_test, majority, bootstrap=True),
    ]
    val_evals = [
        _evaluate("MLP_final_6", "validation", y_val, pred_mlp_val, bootstrap=False),
        _evaluate("WISARD_FINAL_6", "validation", y_val, pred_wis_val, bootstrap=False),
    ]
    mcnemar = _mcnemar(y_test, pred_mlp_test, pred_wis_test)

    # --- Parity closure through the policy pipeline on the whole test set ---
    print("Parity closure via policy pipeline on all test samples...")
    from edge_sim_py import Simulator, User
    from models import Task
    from policies.ml_offloading import create_mlp_offloading_policy, create_wisard_offloading_policy

    simulator = Simulator()
    simulator.initialize(input_file=str(repository_root / "edgesimpy-simulation" / "tutorials" / "datasets" / "sample_dataset2.json"))
    user = User.find_by_id(1)

    def make_tasks():
        return [
            Task(task_id=f"test_{i}", user=user, cpu_cycles=f[0], data_size_mb=f[1], latency_sensitivity=f[2],
                 required_memory_mb=f[3], bandwidth_mbps=f[4], network_latency_ms=f[5],
                 deadline_ms=20000.0, creation_time_s=0.0)
            for i, f in enumerate(dataset.test.X)
        ]

    tasks = make_tasks()
    mlp_policy = create_mlp_offloading_policy(model_path=repository_root / "edgesimpy-simulation" / "models" / "mlp_final_6")
    mlp_policy.load_model()
    wis_policy = create_wisard_offloading_policy()
    wis_policy.fit_model(X_train, y_train)
    assert wis_policy.config.model == WISARD_FINAL_6

    parity = [
        _parity_on_test("MLP_final_6", mlp.predict, X_test,
                        lambda: [mlp_policy.predict(t, simulator.topology).predicted_destination for t in tasks]),
        _parity_on_test("WISARD_FINAL_6", wisard.predict, X_test,
                        lambda: [wis_policy.predict(t, simulator.topology).predicted_destination for t in tasks]),
    ]

    # --- WiSARD seed sensitivity (test) ---
    per_seed = []
    for seed in (7, 11, 23, 42, 101):
        cfg = WiSARDConfig(**{**WISARD_FINAL_6.to_dict(), "seed": seed})
        m = WiSARDModel(cfg); m.fit(X_train, y_train)
        p = m.predict(X_test)
        acc, mf1, bacc = _summary(y_test, p)
        per_seed.append({"seed": seed, "accuracy": acc, "macro_f1": mf1, "balanced_accuracy": bacc,
                         "edge_rate": float(np.mean(p == "Edge"))})
    mf1s = np.array([s["macro_f1"] for s in per_seed])

    payload = {
        "n_test": int(len(y_test)),
        "wisard_config": WISARD_FINAL_6.to_dict(),
        "test": [asdict(e) for e in test_evals],
        "validation": [asdict(e) for e in val_evals],
        "mcnemar_mlp_vs_wisard": mcnemar,
        "parity": parity,
        "wisard_seed_sensitivity": {"per_seed": per_seed, "macro_f1_mean": float(mf1s.mean()), "macro_f1_std": float(mf1s.std())},
    }

    results_dir = repository_root / "edgesimpy-simulation" / "results"
    (results_dir / "final_test_evaluation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_markdown(results_dir / "final_test_evaluation.md", payload)

    print("\n" + "=" * 70)
    for e in test_evals:
        print(f"{e.name:16s} test: acc={e.accuracy:.4f} {_fmt_ci(e.ci95_accuracy)}  macroF1={e.macro_f1:.4f} {_fmt_ci(e.ci95_macro_f1)}  recallCloud={e.recall_cloud:.3f}")
    print(f"McNemar MLP vs WiSARD: {mcnemar['a_correct_b_wrong']} vs {mcnemar['a_wrong_b_correct']} discordant, p={mcnemar['p_value_exact']:.2e}")
    for p in parity:
        print(f"Parity {p['model']}: {p['mismatches']} mismatches / {p['n']} -> {'EXACT' if p['exact'] else 'FAILED'}")
    print(f"WiSARD seed sensitivity (test macro-F1): {mf1s.mean():.4f} ± {mf1s.std():.4f}")
    print(f"Reports: {results_dir / 'final_test_evaluation.md'} / .json")
    return 0 if all(p["exact"] for p in parity) else 1


if __name__ == "__main__":
    raise SystemExit(main())
