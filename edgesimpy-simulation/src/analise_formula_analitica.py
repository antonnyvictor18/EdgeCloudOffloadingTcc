"""Auditoria metodológica da fórmula analítica do simulador C#."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean, median
from typing import Any

# Constantes do simulador C#
EDGE_CAPACITY_CYCLES_PER_MS = 12_000_000
CLOUD_CAPACITY_CYCLES_PER_MS = 60_000_000
AVAILABLE_EDGE_MEMORY_BASE = 8192.0


def analyze_formula(
    cpu_cycles: float,
    task_size_mb: float,
    deadline_ms: float,
    latency_sensitivity: float,
    required_memory_mb: float,
    edge_cpu_usage_percent: float,
    edge_memory_usage_percent: float,
    edge_queue_size: float,
    bandwidth_mbps: float,
    network_latency_ms: float,
    cloud_cpu_usage_percent: float,
    cloud_queue_size: float,
) -> dict[str, Any]:
    """Reconstrói a fórmula analítica exata do EdgeCloudSimulator."""

    # Fatores de CPU
    edge_cpu_factor = 1.0 + edge_cpu_usage_percent / 100.0
    cloud_cpu_factor = 1.0 + cloud_cpu_usage_percent / 180.0

    # Penalidade de memória (apenas Edge)
    available_edge_memory = AVAILABLE_EDGE_MEMORY_BASE * (1.0 - edge_memory_usage_percent / 100.0)
    if required_memory_mb > available_edge_memory:
        memory_penalty = 1.35 + (required_memory_mb - available_edge_memory) / 4096.0
    else:
        memory_penalty = 1.0

    # Tempo de execução
    execution_time_edge_ms = (
        cpu_cycles / EDGE_CAPACITY_CYCLES_PER_MS * edge_cpu_factor * memory_penalty
    )
    execution_time_cloud_ms = cpu_cycles / CLOUD_CAPACITY_CYCLES_PER_MS * cloud_cpu_factor

    # Delays de fila
    edge_queue_delay_ms = edge_queue_size * (18.0 + edge_cpu_usage_percent * 0.45)
    cloud_queue_delay_ms = cloud_queue_size * (10.0 + cloud_cpu_usage_percent * 0.22)

    # Upload e rede
    upload_ms = task_size_mb * 8.0 / max(bandwidth_mbps, 0.1) * 1000.0
    network_penalty_ms = network_latency_ms * (1.0 + latency_sensitivity)

    # Tempo total de resposta
    total_response_time_edge_ms = execution_time_edge_ms + edge_queue_delay_ms
    total_response_time_cloud_ms = (
        execution_time_cloud_ms + cloud_queue_delay_ms + upload_ms + network_penalty_ms
    )

    # Decisão
    best_destination = "Edge" if total_response_time_edge_ms < total_response_time_cloud_ms else "Cloud"

    # Diferença
    difference_ms = total_response_time_edge_ms - total_response_time_cloud_ms

    return {
        "execution_time_edge_ms": execution_time_edge_ms,
        "execution_time_cloud_ms": execution_time_cloud_ms,
        "edge_queue_delay_ms": edge_queue_delay_ms,
        "cloud_queue_delay_ms": cloud_queue_delay_ms,
        "upload_ms": upload_ms,
        "network_penalty_ms": network_penalty_ms,
        "total_response_time_edge_ms": total_response_time_edge_ms,
        "total_response_time_cloud_ms": total_response_time_cloud_ms,
        "best_destination": best_destination,
        "difference_ms": difference_ms,
        "memory_penalty": memory_penalty,
        "available_edge_memory_mb": available_edge_memory,
    }


def analyze_dataset(csv_path: Path) -> dict[str, Any]:
    """Analisa o dataset existente usando a fórmula reconstruída."""

    samples = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sample = {
                "cpu_cycles": float(row["CpuCycles"]),
                "task_size_mb": float(row["TaskSizeMB"]),
                "deadline_ms": float(row["DeadlineMs"]),
                "latency_sensitivity": float(row["LatencySensitivity"]),
                "required_memory_mb": float(row["RequiredMemoryMB"]),
                "edge_cpu_usage_percent": float(row["EdgeCpuUsagePercent"]),
                "edge_memory_usage_percent": float(row["EdgeMemoryUsagePercent"]),
                "edge_queue_size": float(row["EdgeQueueSize"]),
                "bandwidth_mbps": float(row["BandwidthMbps"]),
                "network_latency_ms": float(row["NetworkLatencyMs"]),
                "cloud_cpu_usage_percent": float(row["CloudCpuUsagePercent"]),
                "cloud_queue_size": float(row["CloudQueueSize"]),
                "best_destination": row["BestDestination"],
            }
            samples.append(sample)

    # Reanalisar cada amostra com a fórmula
    results = []
    edge_count = 0
    cloud_count = 0
    tie_count = 0
    differences = []

    for sample in samples:
        # Remover best_destination dos argumentos
        sample_without_label = {k: v for k, v in sample.items() if k != "best_destination"}
        analysis = analyze_formula(**sample_without_label)
        results.append(analysis)

        if analysis["best_destination"] == "Edge":
            edge_count += 1
        elif analysis["best_destination"] == "Cloud":
            cloud_count += 1

        # Verificar empate (diferença muito pequena)
        if abs(analysis["difference_ms"]) < 0.001:
            tie_count += 1

        differences.append(analysis["difference_ms"])

    # Estatísticas da diferença
    differences_abs = [abs(d) for d in differences]
    near_boundary = sum(1 for d in differences_abs if d < 10.0)  # Dentro de 10ms

    return {
        "total_samples": len(samples),
        "edge_count": edge_count,
        "cloud_count": cloud_count,
        "tie_count": tie_count,
        "edge_percentage": edge_count / len(samples) * 100,
        "cloud_percentage": cloud_count / len(samples) * 100,
        "difference_stats": {
            "mean_ms": mean(differences),
            "median_ms": median(differences),
            "min_ms": min(differences),
            "max_ms": max(differences),
            "std_ms": math.sqrt(sum((d - mean(differences)) ** 2 for d in differences) / len(differences)),
        },
        "difference_abs_stats": {
            "mean_ms": mean(differences_abs),
            "median_ms": median(differences_abs),
            "min_ms": min(differences_abs),
            "max_ms": max(differences_abs),
        },
        "near_boundary_count": near_boundary,
        "near_boundary_percentage": near_boundary / len(samples) * 100,
        "samples": results,
    }


def main() -> int:
    """Executa a auditoria da fórmula analítica."""

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"

    if not dataset_path.exists():
        print(f"Dataset não encontrado: {dataset_path}")
        return 1

    print("=" * 80)
    print("AUDITORIA METODOLOGICA DA FORMULA ANALITICA")
    print("=" * 80)

    # Analisar dataset
    analysis = analyze_dataset(dataset_path)

    print(f"\nDistribuição de Labels:")
    print(f"  Total: {analysis['total_samples']}")
    print(f"  Edge: {analysis['edge_count']} ({analysis['edge_percentage']:.2f}%)")
    print(f"  Cloud: {analysis['cloud_count']} ({analysis['cloud_percentage']:.2f}%)")
    print(f"  Empates (~0): {analysis['tie_count']}")

    print(f"\nEstatísticas da Diferença (T_edge - T_cloud):")
    diff_stats = analysis["difference_stats"]
    print(f"  Media: {diff_stats['mean_ms']:.2f} ms")
    print(f"  Mediana: {diff_stats['median_ms']:.2f} ms")
    print(f"  Minimo: {diff_stats['min_ms']:.2f} ms")
    print(f"  Maximo: {diff_stats['max_ms']:.2f} ms")
    print(f"  Desvio padrao: {diff_stats['std_ms']:.2f} ms")

    print(f"\nEstatísticas da Diferença Absoluta:")
    abs_stats = analysis["difference_abs_stats"]
    print(f"  Media: {abs_stats['mean_ms']:.2f} ms")
    print(f"  Mediana: {abs_stats['median_ms']:.2f} ms")
    print(f"  Minimo: {abs_stats['min_ms']:.2f} ms")
    print(f"  Maximo: {abs_stats['max_ms']:.2f} ms")

    print(f"\nAmostras proximas da fronteira (|diff| < 10ms):")
    print(f"  Quantidade: {analysis['near_boundary_count']}")
    print(f"  Porcentagem: {analysis['near_boundary_percentage']:.2f}%")

    # Amostras de exemplo
    print(f"\nExemplos de Amostras:")
    print(f"{'ID':>5} | {'Dest':>5} | {'T_edge':>10} | {'T_cloud':>10} | {'Diff':>10} | {'MemPen':>7}")
    print("-" * 70)

    sample_indices = [0, len(analysis["samples"]) // 2, len(analysis["samples"]) - 1]
    for i in sample_indices:
        result = analysis["samples"][i]
        print(
            f"{i:>5} | {result['best_destination'][:5]:>5} | "
            f"{result['total_response_time_edge_ms']:>10.2f} | "
            f"{result['total_response_time_cloud_ms']:>10.2f} | "
            f"{result['difference_ms']:>10.2f} | "
            f"{result['memory_penalty']:>7.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
