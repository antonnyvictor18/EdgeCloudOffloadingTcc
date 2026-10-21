"""Gera figuras finais (PNG) para o TCC a partir dos resultados consolidados das
Fases 19–24 do pipeline EdgeSimPy.

Figuras produzidas em `results/figures/`:
1. `fig1_preditive_metrics_test_set.png` — Accuracy, macro-F1 e Balanced Accuracy
   (com IC 95%) no test set canônico (n = 2250) para MLP_final_6, WISARD_FINAL_6
   e baseline Majority.
2. `fig2_confusion_matrices_test_set.png` — Matrizes de confusão lado a lado de
   MLP_final_6 e WISARD_FINAL_6 no test set.
3. `fig3_tick_resolution_effect.png` — Efeito da resolução temporal (tick = 1.0 s
   vs 0.1 s, sob FIFO) no tempo médio de conclusão e na taxa de violação de
   deadline por política de destino.
4. `fig4_queue_disciplines_multiworkload.png` — Tempo médio de fila
   (FIFO vs SJF) e taxa de violação de deadline (FIFO vs EDF vs EDF_FEASIBLE)
   na avaliação multi-workload (10 workloads × 20 tasks = 200 tasks).
"""

import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

sns.set_theme(style="whitegrid", context="paper", font_scale=1.25)
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"

POLICY_ORDER = ["AlwaysEdge", "AlwaysCloud", "RandomDestination", "Oracle", "MLP", "WiSARD"]
POLICY_LABELS = {
    "AlwaysEdge": "AlwaysEdge",
    "AlwaysCloud": "AlwaysCloud",
    "RandomDestination": "RandomDest.",
    "Oracle": "Oracle",
    "MLP": "MLP",
    "WiSARD": "WiSARD",
}
QUEUE_LABELS = {
    "fifo": "FIFO",
    "sjf": "SJF",
    "edf": "EDF",
    "llf": "LLF",
    "edf_feasible": "EDF_FEAS.",
}


def plot_test_set_metrics(data: dict) -> None:
    test_entries = [e for e in data["test"]]
    names = [e["name"] for e in test_entries]
    display_names = {
        "MLP_final_6": "MLP",
        "WISARD_FINAL_6": "WiSARD",
        "Majority(Edge)": "Majority\n(AlwaysEdge)",
    }
    metrics = ["accuracy", "macro_f1", "balanced_accuracy"]
    metric_labels = ["Accuracy", "Macro-F1", "Balanced Accuracy"]

    x = np.arange(len(metrics))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#1f77b4", "#ff7f0e", "#7f7f7f"]

    for i, entry in enumerate(test_entries):
        means = [entry[m] for m in metrics]
        ci_errs = []
        for m, ci_key in zip(metrics, ["ci95_accuracy", "ci95_macro_f1", "ci95_balanced_accuracy"]):
            if entry.get(ci_key):
                lo, hi = entry[ci_key]
                ci_errs.append((entry[m] - lo, hi - entry[m]))
            else:
                ci_errs.append((0, 0))
        ci_errs = np.array(ci_errs).T  # shape (2, len(metrics))
        ax.bar(
            x + (i - 1) * width,
            means,
            width,
            yerr=ci_errs,
            capsize=5,
            label=display_names.get(names[i], names[i]),
            color=colors[i],
            edgecolor="black",
            linewidth=0.8,
        )

    ax.set_ylabel("Pontuação")
    ax.set_ylim(0.0, 1.0)
    ax.set_title(
        "Nível Preditivo — Test Set Canônico (n = 2.250, IC 95%)\nMcNemar MLP vs WiSARD: $p = 4.1 \\times 10^{-15}$",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.0), ncol=3, frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    fig.savefig(FIGURES_DIR / "fig1_preditive_metrics_test_set.png")
    plt.close(fig)


def plot_confusion_matrices(data: dict) -> None:
    test_entries = [e for e in data["test"] if e["name"] in ("MLP_final_6", "WISARD_FINAL_6")]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = ["Cloud", "Edge"]
    vmax = 1400

    for ax, entry in zip(axes, test_entries):
        cm = np.array(entry["confusion_matrix"])
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=True,
            ax=ax,
            xticklabels=[f"Pred: {labels[0]}", f"Pred: {labels[1]}"],
            yticklabels=[f"Real: {labels[0]}", f"Real: {labels[1]}"],
            annot_kws={"size": 14, "fontweight": "bold"},
            vmin=0,
            vmax=vmax,
        )
        model_name = "MLP (MLP_final_6)" if "MLP" in entry["name"] else "WiSARD (WISARD_FINAL_6)"
        acc = entry["accuracy"]
        f1 = entry["macro_f1"]
        ax.set_title(f"{model_name}\nAccuracy = {acc*100:.1f}%  |  Macro-F1 = {f1:.3f}", fontsize=12)

    fig.suptitle(
        "Matrizes de Confusão — Test Set Canônico ($n = 2.250$)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_confusion_matrices_test_set.png")
    plt.close(fig)


def plot_tick_resolution_effect(data: dict) -> None:
    rows = data["rows"]
    policies = [p for p in POLICY_ORDER]

    compl_10 = []
    compl_01 = []
    viol_10 = []
    viol_01 = []
    labels = []
    for pol in policies:
        r1 = next(r for r in rows if r["policy"] == pol and abs(r["tick_duration_s"] - 1.0) < 1e-9 and r["queue_policy"] == "fifo")
        r01 = next(r for r in rows if r["policy"] == pol and abs(r["tick_duration_s"] - 0.1) < 1e-9 and r["queue_policy"] == "fifo")
        compl_10.append(r1["mean_completion_time_s"])
        compl_01.append(r01["mean_completion_time_s"])
        viol_10.append(r1["deadline_violation_rate"] * 100)
        viol_01.append(r01["deadline_violation_rate"] * 100)
        labels.append(POLICY_LABELS[pol])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(labels))
    width = 0.35

    axes[0].bar(x - width / 2, compl_10, width, label="tick = 1,0 s (resolução de 1s)", color="#d62728", edgecolor="black")
    axes[0].bar(x + width / 2, compl_01, width, label="tick = 0,1 s (resolução de 100ms)", color="#2ca02c", edgecolor="black")
    axes[0].set_ylabel("Tempo Médio de Conclusão (s)")
    axes[0].set_title("(a) Tempo Médio de Conclusão por Política de Destino", fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=20)
    axes[0].legend()
    axes[0].grid(axis="y", linestyle="--", alpha=0.7)

    axes[1].bar(x - width / 2, viol_10, width, label="tick = 1,0 s (resolução de 1s)", color="#d62728", edgecolor="black")
    axes[1].bar(x + width / 2, viol_01, width, label="tick = 0,1 s (resolução de 100ms)", color="#2ca02c", edgecolor="black")
    axes[1].set_ylabel("Taxa de Violação de Deadline (%)")
    axes[1].set_ylim(0, 100)
    axes[1].set_title("(b) Taxa de Violação de Deadline por Política de Destino", fontweight="bold")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=20)
    axes[1].legend()
    axes[1].grid(axis="y", linestyle="--", alpha=0.7)

    fig.suptitle(
        "Efeito da Resolução Temporal no Sistema (Workloads congelados de 20 tasks, política de fila = FIFO)",
        fontsize=14,
        fontweight="bold",
        y=1.04,
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_tick_resolution_effect.png")
    plt.close(fig)


def plot_multiworkload_queue_disciplines(data: dict) -> None:
    aggregated = data["aggregated"]
    queue_policies = ["fifo", "sjf", "edf", "edf_feasible"]
    policies = POLICY_ORDER
    labels = [POLICY_LABELS[p] for p in policies]

    # Métricas médias de todos os 10 workloads
    compl_sjf = []
    compl_fifo = []
    viol_fifo = []
    viol_edf = []
    viol_edff = []
    viol_sjf = []
    for pol in policies:
        compl_fifo.append(aggregated[f"{pol}__fifo"]["mean_completion_time_s"]["mean"])
        compl_sjf.append(aggregated[f"{pol}__sjf"]["mean_completion_time_s"]["mean"])
        viol_fifo.append(aggregated[f"{pol}__fifo"]["deadline_violation_rate"]["mean"] * 100)
        viol_sjf.append(aggregated[f"{pol}__sjf"]["deadline_violation_rate"]["mean"] * 100)
        viol_edf.append(aggregated[f"{pol}__edf"]["deadline_violation_rate"]["mean"] * 100)
        viol_edff.append(aggregated[f"{pol}__edf_feasible"]["deadline_violation_rate"]["mean"] * 100)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    x = np.arange(len(labels))
    width = 0.35

    # (a) Completion time: FIFO vs SJF
    axes[0].bar(x - width / 2, compl_fifo, width, label="Fila = FIFO", color="#1f77b4", edgecolor="black")
    axes[0].bar(x + width / 2, compl_sjf, width, label="Fila = SJF", color="#ff7f0e", edgecolor="black")
    axes[0].set_ylabel("Tempo Médio de Conclusão (s)")
    axes[0].set_title("(a) Tempo Médio de Conclusão (Redução de Fila via SJF)", fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=20)
    axes[0].legend()
    axes[0].grid(axis="y", linestyle="--", alpha=0.7)

    # (b) Deadline violation: FIFO vs SJF vs EDF vs EDF_FEASIBLE
    x2 = np.arange(len(labels))
    w2 = 0.2
    axes[1].bar(x2 - 1.5 * w2, viol_fifo, w2, label="FIFO", color="#7f7f7f", edgecolor="black")
    axes[1].bar(x2 - 0.5 * w2, viol_sjf, w2, label="SJF", color="#ff7f0e", edgecolor="black")
    axes[1].bar(x2 + 0.5 * w2, viol_edf, w2, label="EDF (cego)", color="#d62728", edgecolor="black")
    axes[1].bar(x2 + 1.5 * w2, viol_edff, w2, label="EDF_FEASIBLE", color="#2ca02c", edgecolor="black")
    axes[1].set_ylabel("Taxa de Violação de Deadline (%)")
    axes[1].set_ylim(0, 100)
    axes[1].set_title("(b) Taxa de Violação de Deadline por Disciplina de Fila", fontweight="bold")
    axes[1].set_xticks(x2)
    axes[1].set_xticklabels(labels, rotation=20)
    axes[1].legend()
    axes[1].grid(axis="y", linestyle="--", alpha=0.7)

    fig.suptitle(
        "Estudo Multi-Workload: 10 Workloads × 20 Tasks = 200 Tasks Executadas no EdgeSimPy\n"
        "(tick = 0,1 s | Edge 12 GHz + LAN 100 Mbps | Cloud 60 GHz + WAN por-Task)",
        fontsize=13,
        fontweight="bold",
        y=1.04,
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig4_queue_disciplines_multiworkload.png")
    plt.close(fig)


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Gerando figuras para o TCC...")
    print(f"Figures directory: {FIGURES_DIR}")

    # Figura 1 e 2: Nível preditivo do test set
    test_eval_path = RESULTS_DIR / "final_test_evaluation.json"
    test_eval = json.loads(test_eval_path.read_text(encoding="utf-8"))
    plot_test_set_metrics(test_eval)
    plot_confusion_matrices(test_eval)

    # Figura 3: Efeito da resolução temporal
    filas_path = RESULTS_DIR / "experimento_filas_e_ticks.json"
    filas = json.loads(filas_path.read_text(encoding="utf-8"))
    plot_tick_resolution_effect(filas)

    # Figura 4: Disciplinas de fila na avaliação multi-workload
    multi_path = RESULTS_DIR / "experimento_multi_workload_sistemico.json"
    multi = json.loads(multi_path.read_text(encoding="utf-8"))
    plot_multiworkload_queue_disciplines(multi)

    print("\nFiguras salvas com sucesso:")
    for fig in sorted(FIGURES_DIR.glob("*.png")):
        print(f"  - {fig.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
