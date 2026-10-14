"""Destination-level policy comparison on the frozen representative workload.

Compares Edge/Cloud *destination* policies end-to-end on the exact same frozen
20-task workload used by experimento_mlp_workload_representativo.py, executing
both destinations in the same EdgeSimPy clock:

    Edge tasks -> NetworkFlow over the EdgeSimPy topology + TaskScheduler (12 GHz)
    Cloud tasks -> logical CloudExecutor (per-Task WAN, FIFO queue, 60 GHz)

Policies compared (decision level only - Edge server selection is identical
for every policy, via NearestServerPolicy, so policies differ ONLY in the
Edge/Cloud destination they choose):

    AlwaysEdge        - sends everything to Edge (Edge-only baseline)
    AlwaysCloud       - sends everything to Cloud (Cloud-only baseline)
    RandomDestination - seeded per-task coin flip (5 seeds, mean +/- sd)
    Oracle            - predicts the analytical BestDestination label; the
                        upper bound *of this closed world* (it reproduces the
                        C# analytical decision, it is not a physical optimum)
    MLP               - frozen MLP_final_6 artifact
    WiSARD            - WISARD_FINAL_6 trained in-session on dataset.train

Circularity note: Oracle reproduces the label-generating analytical formula,
so its systemic advantage reflects consistency with the analytical model, not
an independently discovered optimum. See docs/AI_CONTEXT.md.

Usage: python experimento_comparativo_destinos.py
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from ml.dataset import load_offloading_dataset
from policies.ml_offloading import (
    OffloadingDecision,
    create_mlp_offloading_policy,
    create_wisard_offloading_policy,
)
from experimento_mlp_workload_representativo import (
    EXECUTED_STATUSES,
    RepresentativeWorkloadConfig,
    RepresentativeWorkloadEvaluator,
)


RANDOM_SEEDS = (11, 22, 33, 44, 55)


class StaticDestinationPolicy:
    """Baseline: always predicts the same destination."""

    def __init__(self, destination: str):
        self._destination = destination

    def predict(self, task: Any, topology: Any = None) -> OffloadingDecision:
        return OffloadingDecision(
            predicted_destination=self._destination,
            execution_status="PENDING",
        )


class RandomDestinationPolicy:
    """Baseline: seeded per-task Edge/Cloud coin flip."""

    def __init__(self, seed: int, edge_prob: float = 0.5):
        self._rng = random.Random(seed)
        self._edge_prob = edge_prob

    def predict(self, task: Any, topology: Any = None) -> OffloadingDecision:
        destination = "Edge" if self._rng.random() < self._edge_prob else "Cloud"
        return OffloadingDecision(predicted_destination=destination, execution_status="PENDING")


class OracleDestinationPolicy:
    """Predicts the dataset's analytical BestDestination label for each task.

    Deterministic upper bound of the closed analytical world: by construction
    its predictive accuracy is 1.0 and its decisions are exactly what the C#
    analytical model would choose.
    """

    def __init__(self, labels_by_task_id: Dict[str, str]):
        self._labels = labels_by_task_id

    def predict(self, task: Any, topology: Any = None) -> OffloadingDecision:
        return OffloadingDecision(
            predicted_destination=self._labels[task.task_id],
            execution_status="PENDING",
        )


class DestinationPolicyEvaluator(RepresentativeWorkloadEvaluator):
    """RepresentativeWorkloadEvaluator with an externally supplied policy.

    Bypasses _load_policy so any object implementing
    predict(task, topology) -> OffloadingDecision can drive the same
    frozen-workload evaluation and Edge+Cloud execution engine.
    """

    def __init__(self, config: RepresentativeWorkloadConfig, policy: Any, policy_name: str):
        super().__init__(replace(config, policy=policy_name, experiment_id=f"dest_cmp_{policy_name}"))
        self._injected_policy = policy

    def _load_policy(self) -> Any:
        print(f"Using injected destination policy: {self.config.policy}")
        return self._injected_policy


def _policy_row(policy_name: str, run_label: str, results) -> Dict[str, Any]:
    """Flatten one policy run into a comparison row."""
    sys_all = results.systemic_metrics
    by_dest = sys_all.get("by_destination", {})
    edge = by_dest.get("Edge", {})
    cloud = by_dest.get("Cloud", {})
    edge_pred = sum(1 for r in results.task_results if r.prediction == "Edge")
    cloud_pred = sum(1 for r in results.task_results if r.prediction == "Cloud")
    return {
        "policy": policy_name,
        "run": run_label,
        "edge_predictions": edge_pred,
        "cloud_predictions": cloud_pred,
        "accuracy": results.accuracy,
        "macro_f1": (results.edge_f1 + results.cloud_f1) / 2,
        "executed_tasks": sys_all.get("executed_tasks", 0),
        "executed_edge": edge.get("executed_tasks", 0),
        "executed_cloud": cloud.get("executed_tasks", 0),
        "execution_coverage": results.execution_coverage,
        "mean_completion_time_s": sys_all.get("mean_completion_time_s"),
        "mean_queue_time_s": sys_all.get("mean_queue_time_s"),
        "mean_transmission_time_s": sys_all.get("mean_transmission_time_s"),
        "deadline_violation_rate": sys_all.get("deadline_violation_rate"),
        "edge_mean_completion_s": edge.get("mean_completion_time_s"),
        "cloud_mean_completion_s": cloud.get("mean_completion_time_s"),
        "edge_deadline_violation_rate": edge.get("deadline_violation_rate"),
        "cloud_deadline_violation_rate": cloud.get("deadline_violation_rate"),
        "systemic_metrics": sys_all,
        "confusion_matrix": results.confusion_matrix,
    }


def _aggregate_random(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate RandomDestination seed rows into mean +/- sd."""
    keys = [
        "edge_predictions", "cloud_predictions", "accuracy", "macro_f1",
        "executed_tasks", "executed_edge", "executed_cloud", "execution_coverage",
        "mean_completion_time_s", "mean_queue_time_s", "deadline_violation_rate",
        "edge_mean_completion_s", "cloud_mean_completion_s",
        "edge_deadline_violation_rate", "cloud_deadline_violation_rate",
    ]
    agg = {"policy": "RandomDestination", "run": f"mean over {len(rows)} seeds", "n_seeds": len(rows)}
    for k in keys:
        vals = [r[k] for r in rows if r[k] is not None]
        agg[k] = float(np.mean(vals)) if vals else None
        agg[f"{k}_sd"] = float(np.std(vals)) if len(vals) > 1 else 0.0
    return agg


def generate_report(rows: List[Dict[str, Any]], random_agg: Dict[str, Any], output_path: Path) -> None:
    display_rows = [r for r in rows if r["policy"] != "RandomDestination"]
    if random_agg:
        display_rows.insert(2, random_agg)

    def _f(v, fmt="{:.2f}"):
        return fmt.format(v) if v is not None else "-"

    def _fsd(r, key, fmt="{:.2f}"):
        sd = r.get(f"{key}_sd")
        if sd is None or r["policy"] != "RandomDestination":
            return _f(r.get(key), fmt)
        return f"{r[key]:.2f}±{sd:.2f}" if r.get(key) is not None else "-"

    lines = [
        "# Destination-Level Policy Comparison — Frozen Workload",
        "",
        "All policies evaluated on the **same frozen 20-task workload** (10 Edge-labeled,",
        "10 Cloud-labeled samples) and executed end-to-end: Edge via EdgeSimPy",
        "NetworkFlow + TaskScheduler (12 GHz), Cloud via the logical CloudExecutor",
        "(per-Task WAN attributes, FIFO, 60 GHz). Edge server selection is identical",
        "for every policy (NearestServerPolicy over candidates 2 and 5) — policies",
        "differ only in the Edge/Cloud destination decision.",
        "",
        "## Decision + predictive level",
        "",
        "| Policy | Edge pred | Cloud pred | Accuracy | macro-F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in display_rows:
        lines.append(
            f"| {r['policy']} | {_fsd(r, 'edge_predictions', '{:.1f}')} | "
            f"{_fsd(r, 'cloud_predictions', '{:.1f}')} | {_fsd(r, 'accuracy', '{:.3f}')} | "
            f"{_fsd(r, 'macro_f1', '{:.3f}')} |"
        )

    lines += [
        "",
        "## Execution + systemic level (all executed tasks)",
        "",
        "| Policy | Executed (E/C) | Coverage | Mean completion (s) | Mean queue (s) | Deadline viol. |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in display_rows:
        lines.append(
            f"| {r['policy']} | {r['executed_tasks']} ({r['executed_edge']}/{r['executed_cloud']}) | "
            f"{_f(r['execution_coverage'], '{:.0%}')} | {_fsd(r, 'mean_completion_time_s')} | "
            f"{_fsd(r, 'mean_queue_time_s')} | {_fsd(r, 'deadline_violation_rate', '{:.0%}')} |"
        )

    lines += [
        "",
        "## Systemic level by destination",
        "",
        "| Policy | Edge mean compl. (s) | Edge viol. | Cloud mean compl. (s) | Cloud viol. |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in display_rows:
        lines.append(
            f"| {r['policy']} | {_fsd(r, 'edge_mean_completion_s')} | "
            f"{_fsd(r, 'edge_deadline_violation_rate', '{:.0%}')} | "
            f"{_fsd(r, 'cloud_mean_completion_s')} | "
            f"{_fsd(r, 'cloud_deadline_violation_rate', '{:.0%}')} |"
        )

    lines += [
        "",
        "## Interpretation notes",
        "",
        "- **Oracle** reproduces the analytical BestDestination label; it is the upper",
        "  bound *of this closed world* (decisions identical to the C# analytical model),",
        "  not an independently discovered physical optimum.",
        "- Predictive accuracy != offloading quality: the systemic block is the primary",
        "  evidence — a policy can match labels yet induce worse queues/contention.",
        "- RandomDestination rows aggregate 5 seeds (mean±sd); other policies are",
        "  deterministic on this frozen workload (single run).",
        "- Cloud network cost is per-Task WAN attributes (analytical term) — see the",
        "  circularity note in the module docstring and HISTORICO.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport saved: {output_path}")


def main() -> int:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    base_config = RepresentativeWorkloadConfig()

    # Load the dataset once (for Oracle labels and WiSARD training data)
    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    id_to_label = dict(zip(dataset.all_data.sample_ids, dataset.all_data.y))
    labels_by_task_id = {
        f"task_{i:02d}": id_to_label[sid] for i, sid in enumerate(base_config.frozen_sample_ids)
    }

    def _mlp():
        p = create_mlp_offloading_policy(model_path=Path(__file__).resolve().parents[1] / "models" / "mlp_final_6")
        p.load_model()
        return p

    def _wisard():
        p = create_wisard_offloading_policy()
        p.fit_model(np.array(dataset.train.X), np.array(dataset.train.y))
        return p

    runs: List[tuple[str, Any]] = [
        ("AlwaysEdge", lambda: StaticDestinationPolicy("Edge")),
        ("AlwaysCloud", lambda: StaticDestinationPolicy("Cloud")),
        ("Oracle", lambda: OracleDestinationPolicy(labels_by_task_id)),
        ("MLP", _mlp),
        ("WiSARD", _wisard),
    ]

    rows: List[Dict[str, Any]] = []
    random_rows: List[Dict[str, Any]] = []

    for policy_name, factory in runs:
        print("\n" + "#" * 70)
        print(f"# POLICY: {policy_name}")
        print("#" * 70)
        evaluator = DestinationPolicyEvaluator(base_config, factory(), policy_name)
        res = evaluator.run_evaluation()
        rows.append(_policy_row(policy_name, "single", res))

    for seed in RANDOM_SEEDS:
        print("\n" + "#" * 70)
        print(f"# POLICY: RandomDestination (seed {seed})")
        print("#" * 70)
        evaluator = DestinationPolicyEvaluator(
            base_config, RandomDestinationPolicy(seed=seed), f"Random_s{seed}"
        )
        res = evaluator.run_evaluation()
        random_rows.append(_policy_row("RandomDestination", f"seed={seed}", res))

    random_agg = _aggregate_random(random_rows)

    # ---- Console summary -------------------------------------------------
    print("\n" + "=" * 78)
    print("COMPARISON SUMMARY (frozen 20-task workload, Edge+Cloud executed)")
    print("=" * 78)
    header = f"{'Policy':<20} {'E/C pred':>9} {'Acc':>6} {'Exec':>10} {'Compl(s)':>9} {'Viol%':>7}"
    print(header)
    print("-" * 78)
    for r in rows:
        print(
            f"{r['policy']:<20} {r['edge_predictions']:>4}/{r['cloud_predictions']:<4} "
            f"{r['accuracy']:>6.3f} {r['executed_edge']:>5}+{r['executed_cloud']:<4} "
            f"{r['mean_completion_time_s'] or 0:>9.2f} {(r['deadline_violation_rate'] or 0):>6.0%}"
        )
    print(
        f"{'RandomDestination':<20} {random_agg['edge_predictions']:>4.1f}/{random_agg['cloud_predictions']:>4.1f} "
        f"{random_agg['accuracy']:>6.3f} {random_agg['executed_edge']:>5.1f}+{random_agg['executed_cloud']:>4.1f} "
        f"{random_agg['mean_completion_time_s'] or 0:>9.2f} {(random_agg['deadline_violation_rate'] or 0):>6.0%}"
    )

    # ---- Persist ---------------------------------------------------------
    md_path = results_dir / "comparativo_destinos_workload.md"
    json_path = results_dir / "comparativo_destinos_workload.json"
    generate_report(rows, random_agg, md_path)
    json_path.write_text(
        json.dumps(
            {
                "experiment_id": "comparativo_destinos_workload_v1",
                "frozen_sample_ids": list(base_config.frozen_sample_ids),
                "random_seeds": list(RANDOM_SEEDS),
                "policies": rows,
                "random_destination": {"per_seed": random_rows, "aggregate": random_agg},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"JSON saved: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
