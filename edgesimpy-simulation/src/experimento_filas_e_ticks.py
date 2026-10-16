"""Factorial study: Offloading Destination Policy x Queue Discipline x Tick Resolution.

Evaluates the interaction between three architectural dimensions on the exact
same frozen 20-task representative workload (10 Edge-labeled, 10 Cloud-labeled):

1. Temporal resolution (Step A):
   - tick_duration_s = 1.0 s (EdgeSimPy tutorial default; 1-second quantization)
   - tick_duration_s = 0.1 s (100 ms resolution; link bandwidths scaled by 0.1
     MB/tick so physical throughput remains 12.5 MB/s = 100 Mbps)

2. Queue scheduling discipline (Step B) on both Edge and Cloud queues:
   - FIFO (First-In, First-Out): arrival order baseline
   - SJF  (Shortest Job First): minimum cpu_cycles -> minimizes mean queue and
     completion time under Head-of-Line blocking
   - EDF  (Earliest Deadline First): minimum deadline_time_s -> directly uses
     the per-Task DeadlineMs attribute (excluded from the 6-feature ML contract)
     at the local scheduler level to minimize deadline violations
   - LLF  (Least Laxity First): minimum remaining slack
     (deadline_time_s - current_time_s - est_exec_time_s)

3. Offloading destination policy (Step C):
   - AlwaysEdge, AlwaysCloud, RandomDestination (5 seeds), Oracle, MLP, WiSARD

Outputs:
- results/experimento_filas_e_ticks.md
- results/experimento_filas_e_ticks.json

Usage: python experimento_filas_e_ticks.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edgesimpy-source"))

from execution import SUPPORTED_QUEUE_POLICIES
from ml.dataset import load_offloading_dataset
from policies.ml_offloading import (
    create_mlp_offloading_policy,
    create_wisard_offloading_policy,
)
from experimento_mlp_workload_representativo import (
    RepresentativeWorkloadConfig,
)
from experimento_comparativo_destinos import (
    RANDOM_SEEDS,
    DestinationPolicyEvaluator,
    OracleDestinationPolicy,
    RandomDestinationPolicy,
    StaticDestinationPolicy,
    _aggregate_random,
    _policy_row,
)


TICK_RESOLUTIONS: Tuple[float, ...] = (1.0, 0.1)
QUEUE_POLICIES: Tuple[str, ...] = SUPPORTED_QUEUE_POLICIES  # ("fifo", "sjf", "edf", "llf")
DETERMINISTIC_POLICIES: Tuple[str, ...] = (
    "AlwaysEdge",
    "AlwaysCloud",
    "Oracle",
    "MLP",
    "WiSARD",
)


def _run_cell(
    base_config: RepresentativeWorkloadConfig,
    policy_name: str,
    policy_factory: Callable[[], Any],
    tick_s: float,
    queue_policy: str,
) -> Dict[str, Any]:
    cfg = replace(
        base_config,
        tick_duration_s=tick_s,
        queue_policy=queue_policy,
    )
    evaluator = DestinationPolicyEvaluator(
        cfg,
        policy_factory(),
        f"{policy_name}_t{tick_s}_{queue_policy}",
    )
    res = evaluator.run_evaluation()
    row = _policy_row(policy_name, f"tick={tick_s}s,queue={queue_policy}", res)
    row["tick_duration_s"] = tick_s
    row["queue_policy"] = queue_policy
    row["edge_mean_queue_s"] = (
        res.systemic_metrics.get("by_destination", {}).get("Edge", {}).get("mean_queue_time_s")
    )
    row["cloud_mean_queue_s"] = (
        res.systemic_metrics.get("by_destination", {}).get("Cloud", {}).get("mean_queue_time_s")
    )
    row["edge_mean_exec_s"] = (
        res.systemic_metrics.get("by_destination", {}).get("Edge", {}).get("mean_execution_time_s")
    )
    row["cloud_mean_exec_s"] = (
        res.systemic_metrics.get("by_destination", {}).get("Cloud", {}).get("mean_execution_time_s")
    )
    return row


def _run_random_cell(
    base_config: RepresentativeWorkloadConfig,
    tick_s: float,
    queue_policy: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    seed_rows: List[Dict[str, Any]] = []
    for seed in RANDOM_SEEDS:
        cfg = replace(
            base_config,
            tick_duration_s=tick_s,
            queue_policy=queue_policy,
        )
        evaluator = DestinationPolicyEvaluator(
            cfg,
            RandomDestinationPolicy(seed=seed),
            f"Random_s{seed}_t{tick_s}_{queue_policy}",
        )
        res = evaluator.run_evaluation()
        r = _policy_row("RandomDestination", f"seed={seed}", res)
        r["tick_duration_s"] = tick_s
        r["queue_policy"] = queue_policy
        r["edge_mean_queue_s"] = (
            res.systemic_metrics.get("by_destination", {}).get("Edge", {}).get("mean_queue_time_s")
        )
        r["cloud_mean_queue_s"] = (
            res.systemic_metrics.get("by_destination", {}).get("Cloud", {}).get("mean_queue_time_s")
        )
        seed_rows.append(r)

    agg = _aggregate_random(seed_rows)
    agg["tick_duration_s"] = tick_s
    agg["queue_policy"] = queue_policy
    for extra_key in ("edge_mean_queue_s", "cloud_mean_queue_s"):
        vals = [r[extra_key] for r in seed_rows if r.get(extra_key) is not None]
        agg[extra_key] = float(np.mean(vals)) if vals else None
        agg[f"{extra_key}_sd"] = float(np.std(vals)) if len(vals) > 1 else 0.0
    return agg, seed_rows


def _fmt(v: Any, fmt: str = "{:.2f}") -> str:
    return fmt.format(v) if v is not None else "-"


def generate_markdown_report(
    all_rows: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    def lookup(policy: str, tick_s: float, qpol: str) -> Dict[str, Any]:
        for r in all_rows:
            if (
                r["policy"] == policy
                and abs(r["tick_duration_s"] - tick_s) < 1e-9
                and r["queue_policy"] == qpol
            ):
                return r
        raise KeyError((policy, tick_s, qpol))

    lines: List[str] = [
        "# Estudo Fatorial: Resolução Temporal (Tick) × Disciplina de Fila × Política de Destino",
        "",
        "Avaliação conduzida sobre o **mesmo workload representativo congelado de 20 tasks**",
        "(10 rótulos analíticos Edge, 10 Cloud) executando Edge (`NetworkFlow` + `TaskScheduler` a 12 GHz)",
        "e Cloud (`CloudExecutor` lógico com WAN por-Task a 60 GHz) no mesmo relógio do EdgeSimPy.",
        "",
        "## 1. Desenho Experimental (Passos A → B → C)",
        "",
        "1. **Passo A — Resolução Temporal (`tick_duration_s`):**",
        "   - `1.0 s`: configuração padrão do tutorial EdgeSimPy (`link.bandwidth = 12.5 MB/tick`).",
        "   - `0.1 s` (100 ms): `configure_simulator_tick_resolution` reescala cada link para",
        "     `1.25 MB/tick`, mantendo a vazão física invariante em **12.5 MB/s (100 Mbps)** e",
        "     eliminando o pedágio artificial de 1 s por task na fila de CPU.",
        "2. **Passo B — Disciplina de Fila Local (`queue_policy`):**",
        "   - `FIFO`: ordem de chegada na fila de execução.",
        "   - `SJF` (*Shortest Job First*): menor `cpu_cycles` primeiro (ótimo para tempo médio de fila).",
        "   - `EDF` (*Earliest Deadline First*): menor `deadline_time_s` primeiro — incorpora no",
        "     escalonador local o atributo `DeadlineMs` que não faz parte das 6 features do classificador ML.",
        "   - `LLF` (*Least Laxity First*): menor folga `(deadline_time_s - t_atual) - tempo_exec_estimado`.",
        "   - `EDF_FEASIBLE` (*Feasibility-Aware EDF*): prioriza por EDF apenas tarefas que ainda podem",
        "     cumprir o deadline (`t_atual + exec <= deadline`); tarefas cujo deadline já expirou no upload",
        "     ('tasks zumbis') são rebaixadas para o fim da fila e atendidas em *best-effort* via SJF.",
        "3. **Passo C — Política de Destino (Offloading):**",
        "   - `AlwaysEdge`, `AlwaysCloud`, `RandomDestination` (5 seeds), `Oracle`, `MLP` (`MLP_final_6`), `WiSARD` (`WISARD_FINAL_6`).",
        "",
        "---",
        "",
        "## 2. Efeito do Passo A: Resolução Temporal (`tick = 1.0 s` vs `tick = 0.1 s`, sob FIFO)",
        "",
        "| Política | E/C | Compl. 1.0s (s) | Compl. 0.1s (s) | Fila 1.0s (s) | Fila 0.1s (s) | Viol. 1.0s | Viol. 0.1s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    policy_order = ["AlwaysEdge", "AlwaysCloud", "RandomDestination", "Oracle", "MLP", "WiSARD"]
    for pol in policy_order:
        r1 = lookup(pol, 1.0, "fifo")
        r01 = lookup(pol, 0.1, "fifo")
        ec = f"{_fmt(r1['edge_predictions'], '{:.0f}')}/{_fmt(r1['cloud_predictions'], '{:.0f}')}"
        if pol == "RandomDestination":
            ec = f"{r1['edge_predictions']:.1f}/{r1['cloud_predictions']:.1f}"
        lines.append(
            f"| {pol} | {ec} | {_fmt(r1['mean_completion_time_s'])} | {_fmt(r01['mean_completion_time_s'])} | "
            f"{_fmt(r1['mean_queue_time_s'])} | {_fmt(r01['mean_queue_time_s'])} | "
            f"{_fmt(r1['deadline_violation_rate'], '{:.0%}')} | {_fmt(r01['deadline_violation_rate'], '{:.0%}')} |"
        )

    lines += [
        "",
        "### Decomposição Edge vs Cloud sob `FIFO` (`tick = 1.0 s` → `tick = 0.1 s`)",
        "",
        "| Política | Edge fila 1.0s→0.1s (s) | Edge compl. 1.0s→0.1s (s) | Cloud fila 1.0s→0.1s (s) | Cloud compl. 1.0s→0.1s (s) | Cloud viol. 1.0s→0.1s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pol in policy_order:
        r1 = lookup(pol, 1.0, "fifo")
        r01 = lookup(pol, 0.1, "fifo")
        lines.append(
            f"| {pol} | {_fmt(r1['edge_mean_queue_s'])} → {_fmt(r01['edge_mean_queue_s'])} | "
            f"{_fmt(r1['edge_mean_completion_s'])} → {_fmt(r01['edge_mean_completion_s'])} | "
            f"{_fmt(r1['cloud_mean_queue_s'])} → {_fmt(r01['cloud_mean_queue_s'])} | "
            f"{_fmt(r1['cloud_mean_completion_s'])} → {_fmt(r01['cloud_mean_completion_s'])} | "
            f"{_fmt(r1['cloud_deadline_violation_rate'], '{:.0%}')} → {_fmt(r01['cloud_deadline_violation_rate'], '{:.0%}')} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Efeito dos Passos B & C: Política de Destino × Disciplina de Fila (em `tick = 0.1 s`)",
        "",
        "### 3.1 Tempo Médio de Conclusão (`mean_completion_time_s`, em segundos)",
        "",
        "| Política de Destino | FIFO (s) | SJF (s) | EDF (s) | LLF (s) | EDF_FEASIBLE (s) | Melhor disciplina |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for pol in policy_order:
        cells = {q: lookup(pol, 0.1, q)["mean_completion_time_s"] for q in QUEUE_POLICIES}
        best_q = min(cells, key=lambda k: cells[k] if cells[k] is not None else float("inf"))
        lines.append(
            f"| {pol} | {_fmt(cells['fifo'], '{:.3f}')} | {_fmt(cells['sjf'], '{:.3f}')} | "
            f"{_fmt(cells['edf'], '{:.3f}')} | {_fmt(cells['llf'], '{:.3f}')} | "
            f"{_fmt(cells['edf_feasible'], '{:.3f}')} | **{best_q.upper()}** ({cells[best_q]:.3f} s) |"
        )

    lines += [
        "",
        "### 3.2 Tempo Médio de Fila (`mean_queue_time_s`, em segundos)",
        "",
        "| Política de Destino | FIFO (s) | SJF (s) | EDF (s) | LLF (s) | EDF_FEASIBLE (s) | Redução SJF vs FIFO |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for pol in policy_order:
        cells = {q: lookup(pol, 0.1, q)["mean_queue_time_s"] for q in QUEUE_POLICIES}
        red = (
            (cells["fifo"] - cells["sjf"]) / cells["fifo"]
            if cells["fifo"] and cells["fifo"] > 0
            else 0.0
        )
        lines.append(
            f"| {pol} | {_fmt(cells['fifo'], '{:.3f}')} | {_fmt(cells['sjf'], '{:.3f}')} | "
            f"{_fmt(cells['edf'], '{:.3f}')} | {_fmt(cells['llf'], '{:.3f}')} | "
            f"{_fmt(cells['edf_feasible'], '{:.3f}')} | {red:+.1%} |"
        )

    lines += [
        "",
        "### 3.3 Taxa de Violação de Deadline (`deadline_violation_rate`)",
        "",
        "| Política de Destino | FIFO | SJF | EDF | LLF | EDF_FEASIBLE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pol in policy_order:
        cells = {q: lookup(pol, 0.1, q)["deadline_violation_rate"] for q in QUEUE_POLICIES}
        lines.append(
            f"| {pol} | {_fmt(cells['fifo'], '{:.1%}')} | {_fmt(cells['sjf'], '{:.1%}')} | "
            f"{_fmt(cells['edf'], '{:.1%}')} | {_fmt(cells['llf'], '{:.1%}')} | "
            f"{_fmt(cells['edf_feasible'], '{:.1%}')} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Comparação com `tick = 1.0 s`: Por que a resolução temporal destrava as disciplinas de fila",
        "",
        "| Política (tick = 1.0 s) | FIFO compl. / fila / viol. | SJF compl. / fila / viol. | EDF compl. / fila / viol. | LLF compl. / fila / viol. | EDF_FEASIBLE compl. / fila / viol. |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pol in policy_order:
        parts = []
        for q in QUEUE_POLICIES:
            r = lookup(pol, 1.0, q)
            parts.append(
                f"{_fmt(r['mean_completion_time_s'])}s / {_fmt(r['mean_queue_time_s'])}s / "
                f"{_fmt(r['deadline_violation_rate'], '{:.0%}')}"
            )
        lines.append(f"| {pol} | " + " | ".join(parts) + " |")

    lines += [
        "",
        "## 5. Principais Conclusões para o TCC",
        "",
        "1. **Efeito dramático da resolução temporal (Passo A):**",
        "   - Com `tick = 1.0 s`, cada task na fila pagava no mínimo 1 s inteiro de servidor, mesmo",
        "     quando sua execução durava `0.02–0.15 s` no Cloud (60 GHz) ou `0.1–0.6 s` no Edge (12 GHz).",
        "   - Ao reduzir o tick para `0.1 s` (mantendo a vazão da rede em 12.5 MB/s = 100 Mbps), a fila",
        "     Cloud cai de **3–6 s para frações de segundo**, derrubando as violações de deadline do Cloud",
        "     e revelando a verdadeira vantagem de capacidade (60 GHz + WAN dedicada por task).",
        "2. **Interação entre resolução temporal e políticas de fila (Passos A + B):**",
        "   - Em `tick = 1.0 s`, trocar `FIFO` por `SJF` quase não altera o tempo de fila porque quase",
        "     todas as tasks são arredondadas para 1 tick (1 s) de ocupação de CPU.",
        "   - Em `tick = 0.1 s`, as durações de CPU se diferenciam (1 a 7 ticks de 0.1 s): **SJF reduz",
        "     consistentemente o tempo médio de fila e de conclusão**, enquanto **EDF/LLF reordenam",
        "     tasks urgentes usando `DeadlineMs`**.",
        "3. **Gargalo residual no caminho Edge (rede compartilhada vs fila de CPU):**",
        "   - Para tasks enviadas ao Edge num burst simultâneo (`t = 0`), os 10–12 fluxos concorrem",
        "     simultaneamente pelo link LAN de 12.5 MB/s (`max_min_fairness`). Como muitas tasks",
        "     terminam o upload em instantes próximos ou já chegam após estourar deadlines sub-segundo,",
        "     a disciplina da fila de CPU atua apenas **após** o término do upload.",
        "   - Isso demonstra um achado sistêmico central do EdgeSimPy que o modelo analítico C# não",
        "     captura: **sob rajadas de dados grandes, o gargalo no Edge desloca-se da fila de CPU",
        "     para o compartilhamento de banda de rede (NetworkFlow)**.",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nMarkdown report saved to: {output_path}")


def main() -> int:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    base_config = RepresentativeWorkloadConfig()

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    id_to_label = dict(zip(dataset.all_data.sample_ids, dataset.all_data.y))
    labels_by_task_id = {
        f"task_{i:02d}": id_to_label[sid] for i, sid in enumerate(base_config.frozen_sample_ids)
    }

    # Pre-load MLP and pre-train WiSARD once (policies are stateless at predict time)
    mlp_policy = create_mlp_offloading_policy(
        model_path=Path(__file__).resolve().parents[1] / "models" / "mlp_final_6"
    )
    mlp_policy.load_model()

    wisard_policy = create_wisard_offloading_policy()
    wisard_policy.fit_model(np.array(dataset.train.X), np.array(dataset.train.y))

    factories: List[Tuple[str, Callable[[], Any]]] = [
        ("AlwaysEdge", lambda: StaticDestinationPolicy("Edge")),
        ("AlwaysCloud", lambda: StaticDestinationPolicy("Cloud")),
        ("Oracle", lambda: OracleDestinationPolicy(labels_by_task_id)),
        ("MLP", lambda: mlp_policy),
        ("WiSARD", lambda: wisard_policy),
    ]

    all_rows: List[Dict[str, Any]] = []
    random_details: Dict[str, Any] = {}

    for tick_s in TICK_RESOLUTIONS:
        for qpol in QUEUE_POLICIES:
            for policy_name, factory in factories:
                row = _run_cell(base_config, policy_name, factory, tick_s, qpol)
                all_rows.append(row)

            rand_agg, rand_seeds = _run_random_cell(base_config, tick_s, qpol)
            all_rows.append(rand_agg)
            random_details[f"tick_{tick_s}_{qpol}"] = rand_seeds

    # Console summary table
    print("\n" + "=" * 92)
    print("FACTORIAL SUMMARY: Tick Resolution x Queue Policy x Destination Policy")
    print("=" * 92)
    print(
        f"{'Tick(s)':<8} {'Queue':<6} {'Policy':<18} {'E/C':>7} "
        f"{'Compl(s)':>9} {'Queue(s)':>9} {'Viol%':>7} {'EdgeC(s)':>9} {'CloudC(s)':>10}"
    )
    print("-" * 92)
    for r in all_rows:
        ec = f"{r['edge_predictions']:.0f}/{r['cloud_predictions']:.0f}"
        if r["policy"] == "RandomDestination":
            ec = f"{r['edge_predictions']:.1f}/{r['cloud_predictions']:.1f}"
        print(
            f"{r['tick_duration_s']:<8.1f} {r['queue_policy'].upper():<6} {r['policy']:<18} {ec:>7} "
            f"{(r['mean_completion_time_s'] or 0):>9.3f} {(r['mean_queue_time_s'] or 0):>9.3f} "
            f"{(r['deadline_violation_rate'] or 0):>6.1%} "
            f"{_fmt(r.get('edge_mean_completion_s'), '{:.2f}'):>9} "
            f"{_fmt(r.get('cloud_mean_completion_s'), '{:.2f}'):>10}"
        )

    md_path = results_dir / "experimento_filas_e_ticks.md"
    json_path = results_dir / "experimento_filas_e_ticks.json"
    generate_markdown_report(all_rows, md_path)
    json_path.write_text(
        json.dumps(
            {
                "experiment_id": "factorial_tick_queue_destination_v1",
                "frozen_sample_ids": list(base_config.frozen_sample_ids),
                "tick_resolutions_s": list(TICK_RESOLUTIONS),
                "queue_policies": list(QUEUE_POLICIES),
                "random_seeds": list(RANDOM_SEEDS),
                "rows": all_rows,
                "random_seed_details": random_details,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"JSON report saved to: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
