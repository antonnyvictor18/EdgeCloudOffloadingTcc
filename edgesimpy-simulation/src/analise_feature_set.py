"""Análise estruturada do feature set para geração de labels."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

# Constantes do simulador C#
EDGE_CAPACITY_CYCLES_PER_MS = 12_000_000
CLOUD_CAPACITY_CYCLES_PER_MS = 60_000_000
AVAILABLE_EDGE_MEMORY_BASE = 8192.0


def analyze_formula_participation(
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
    """Analisa a participação de cada feature na fórmula analítica."""

    participation = {
        "CpuCycles": {"participa": True, "onde": ["T_edge", "T_cloud"], "papel": "divisao base"},
        "TaskSizeMB": {"participa": True, "onde": ["T_cloud"], "papel": "upload"},
        "DeadlineMs": {"participa": False, "onde": [], "papel": "avaliacao posterior"},
        "LatencySensitivity": {"participa": True, "onde": ["T_cloud"], "papel": "penalidade rede"},
        "RequiredMemoryMB": {"participa": True, "onde": ["T_edge"], "papel": "penalidade memoria"},
        "EdgeCpuUsagePercent": {"participa": True, "onde": ["T_edge"], "papel": "fator CPU e fila"},
        "EdgeMemoryUsagePercent": {"participa": True, "onde": ["T_edge"], "papel": "disponibilidade memoria"},
        "EdgeQueueSize": {"participa": True, "onde": ["T_edge"], "papel": "fila"},
        "BandwidthMbps": {"participa": True, "onde": ["T_cloud"], "papel": "upload"},
        "NetworkLatencyMs": {"participa": True, "onde": ["T_cloud"], "papel": "penalidade rede"},
        "CloudCpuUsagePercent": {"participa": True, "onde": ["T_cloud"], "papel": "fator CPU e fila"},
        "CloudQueueSize": {"participa": True, "onde": ["T_cloud"], "papel": "fila"},
    }

    return participation


def check_dataset_availability(csv_path: Path) -> dict[str, bool]:
    """Verifica quais features estão disponíveis no dataset."""

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])

    features = [
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
    ]

    availability = {feature: feature in columns for feature in features}

    return availability


def check_edgesimpy_availability() -> dict[str, bool]:
    """Verifica quais features estão disponíveis no EdgeSimPy no momento da decisão."""

    # Features que podem ser observadas no EdgeSimPy antes da decisão
    edgesimpy_available = {
        "CpuCycles": True,  # Requisito da Task
        "TaskSizeMB": True,  # Requisito da Task
        "DeadlineMs": True,  # Requisito da Task
        "LatencySensitivity": True,  # Requisito da Task
        "RequiredMemoryMB": True,  # Requisito da Task
        "EdgeCpuUsagePercent": False,  # Estado analítico, não observável nativamente
        "EdgeMemoryUsagePercent": False,  # Estado analítico, não observável nativamente
        "EdgeQueueSize": False,  # Fila de Tasks do TCC, não nativa do EdgeSimPy
        "BandwidthMbps": True,  # Pode ser inferido da topologia
        "NetworkLatencyMs": True,  # Pode ser calculado da topologia
        "CloudCpuUsagePercent": False,  # Cloud não implementada
        "CloudQueueSize": False,  # Cloud não implementada
    }

    return edgesimpy_available


def create_feature_matrix(csv_path: Path) -> dict[str, dict[str, str]]:
    """Cria matriz completa feature × fórmula × dataset × EdgeSimPy."""

    participation = analyze_formula_participation(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    dataset_available = check_dataset_availability(csv_path)
    edgesimpy_available = check_edgesimpy_availability()

    matrix = {}
    for feature in participation.keys():
        matrix[feature] = {
            "participa_label": participation[feature]["participa"],
            "esta_dataset": dataset_available[feature],
            "disponivel_edgesimpy": edgesimpy_available[feature],
            "situacao": _classify_situation(
                participation[feature]["participa"],
                dataset_available[feature],
                edgesimpy_available[feature],
            ),
        }

    return matrix


def _classify_situation(participa: bool, dataset: bool, edgesimpy: bool) -> str:
    """Classifica a situação de cada feature."""

    if not participa:
        if dataset and edgesimpy:
            return "disponivel mas nao usada no label"
        elif dataset and not edgesimpy:
            return "disponivel no dataset mas nao usada nem observavel"
        else:
            return "nao usada nem disponivel"

    if participa:
        if dataset and edgesimpy:
            return "causal e observavel"
        elif dataset and not edgesimpy:
            return "causal mas nao observavel no EdgeSimPy"
        elif not dataset and edgesimpy:
            return "causal mas nao esta no dataset"
        else:
            return "causal mas indisponivel"


def main() -> int:
    """Executa a análise estruturada do feature set."""

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"

    if not dataset_path.exists():
        print(f"Dataset não encontrado: {dataset_path}")
        return 1

    print("=" * 100)
    print("ANALISE ESTRUTURADA DO FEATURE SET")
    print("=" * 100)

    # Criar matriz
    matrix = create_feature_matrix(dataset_path)

    # Imprimir tabela
    print(f"\n{'Feature':<25} | {'Participa Label?':<17} | {'Esta Dataset?':<15} | {'Disp. EdgeSimPy?':<17} | {'Situacao':<40}")
    print("-" * 100)

    for feature, data in sorted(matrix.items()):
        print(
            f"{feature:<25} | {str(data['participa_label']):<17} | "
            f"{str(data['esta_dataset']):<15} | {str(data['disponivel_edgesimpy']):<17} | "
            f"{data['situacao']:<40}"
        )

    # Análise de consistência
    print("\n" + "=" * 100)
    print("ANALISE DE CONSISTENCIA")
    print("=" * 100)

    causal_features = [f for f, d in matrix.items() if d["participa_label"]]
    available_in_dataset = [f for f, d in matrix.items() if d["esta_dataset"]]
    available_in_edgesimpy = [f for f, d in matrix.items() if d["disponivel_edgesimpy"]]

    print(f"\nFeatures que participam do label: {len(causal_features)}")
    print(f"Features disponíveis no dataset: {len(available_in_dataset)}")
    print(f"Features disponíveis no EdgeSimPy: {len(available_in_edgesimpy)}")

    # Features causais mas não observáveis
    causal_not_observable = [
        f for f in causal_features if not matrix[f]["disponivel_edgesimpy"]
    ]
    print(f"\nFeatures causais mas NAO observaveis no EdgeSimPy: {len(causal_not_observable)}")
    for f in causal_not_observable:
        print(f"  - {f}")

    # Features observáveis mas não causais
    observable_not_causal = [
        f for f in available_in_edgesimpy if not matrix[f]["participa_label"]
    ]
    print(f"\nFeatures observaveis mas NAO causais: {len(observable_not_causal)}")
    for f in observable_not_causal:
        print(f"  - {f}")

    # Consistência do contrato ML atual
    print("\n" + "=" * 100)
    print("CONSISTENCIA DO CONTRATO ML ATUAL")
    print("=" * 100)

    ml_contract_features = [
        "CpuCycles",
        "TaskSizeMB",
        "DeadlineMs",
        "LatencySensitivity",
        "RequiredMemoryMB",
    ]

    print(f"\nFeatures do contrato ML atual: {len(ml_contract_features)}")
    for f in ml_contract_features:
        data = matrix[f]
        print(f"  - {f}: {data['situacao']}")

    # Features causais que foram removidas
    causal_removed = [
        f for f in causal_features if f not in ml_contract_features
    ]
    print(f"\nFeatures causais REMOVIDAS do contrato ML: {len(causal_removed)}")
    for f in causal_removed:
        data = matrix[f]
        print(f"  - {f}: {data['situacao']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
