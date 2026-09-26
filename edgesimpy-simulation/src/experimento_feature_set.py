"""Experimento controlado de feature set: comparação de MLP com diferentes configurações de features."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.dataset_full import FULL_FEATURE_NAMES, load_full_offloading_dataset
from ml.metrics import ClassificationMetrics, compute_metrics, format_metrics_table
from ml.mlp_model import MLPConfig, MLPModel


def create_feature_variants(
    X_full: np.ndarray,
    feature_names: tuple[str, ...],
) -> dict[str, tuple[np.ndarray, tuple[str, ...]]]:
    """Cria diferentes variantes de feature set."""

    # Feature set atual do contrato ML (5 features)
    current_features = (
        "CpuCycles",
        "TaskSizeMB",
        "DeadlineMs",
        "LatencySensitivity",
        "RequiredMemoryMB",
    )

    # Variante 1: Feature set atual (5 features)
    current_indices = [i for i, name in enumerate(feature_names) if name in current_features]
    X_current = X_full[:, current_indices]

    # Variante 2: Sem DeadlineMs (4 features)
    current_without_deadline = [name for name in current_features if name != "DeadlineMs"]
    no_deadline_indices = [i for i, name in enumerate(feature_names) if name in current_without_deadline]
    X_no_deadline = X_full[:, no_deadline_indices]

    # Variante 3: Features causais observáveis (6 features)
    # Adiciona BandwidthMbps e NetworkLatencyMs ao conjunto atual
    causal_observable = list(current_features) + ["BandwidthMbps", "NetworkLatencyMs"]
    causal_indices = [i for i, name in enumerate(feature_names) if name in causal_observable]
    X_causal = X_full[:, causal_indices]

    return {
        "current": (X_current, current_features),
        "no_deadline": (X_no_deadline, tuple(current_without_deadline)),
        "causal_observable": (X_causal, tuple(causal_observable)),
    }


def train_and_compare_variants(
    dataset,
    variants: dict[str, tuple[np.ndarray, tuple[str, ...]]],
) -> dict[str, Any]:
    """Treina MLP com diferentes variantes de feature set."""

    results = {
        "dataset_info": dataset.to_dict(),
        "variants": {},
    }

    # Configuração MLP fixa
    mlp_config = MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11)

    for variant_name, (X_variant, feature_names) in variants.items():
        print(f"\n{'='*60}")
        print(f"Treinando variante: {variant_name}")
        print(f"Features: {list(feature_names)}")
        print(f"Feature count: {len(feature_names)}")
        print(f"{'='*60}")

        # Preparar dados
        X_train = np.array(dataset.train.X)
        y_train = np.array(dataset.train.y)
        X_val = np.array(dataset.validation.X)
        y_val = np.array(dataset.validation.y)
        X_test = np.array(dataset.test.X)
        y_test = np.array(dataset.test.y)

        # Mapear índices para esta variante
        full_feature_names = FULL_FEATURE_NAMES
        variant_indices = [i for i, name in enumerate(full_feature_names) if name in feature_names]

        X_train_variant = X_train[:, variant_indices]
        X_val_variant = X_val[:, variant_indices]
        X_test_variant = X_test[:, variant_indices]

        # Treinar MLP
        model = MLPModel(mlp_config)
        model.fit(X_train_variant, y_train)

        # Validar
        y_val_pred = model.predict(X_val_variant)
        val_metrics = compute_metrics(y_val, y_val_pred)
        print(f"Validation Accuracy: {val_metrics.accuracy:.4f}")
        print(f"Validation F1 Edge: {val_metrics.f1_edge:.4f}")
        print(f"Validation F1 Cloud: {val_metrics.f1_cloud:.4f}")

        # Testar
        y_test_pred = model.predict(X_test_variant)
        test_metrics = compute_metrics(y_test, y_test_pred)
        print(f"Test Accuracy: {test_metrics.accuracy:.4f}")
        print(f"Test F1 Edge: {test_metrics.f1_edge:.4f}")
        print(f"Test F1 Cloud: {test_metrics.f1_cloud:.4f}")

        # Armazenar resultados
        results["variants"][variant_name] = {
            "feature_names": list(feature_names),
            "feature_count": len(feature_names),
            "validation": val_metrics.to_dict(),
            "test": test_metrics.to_dict(),
            "config": mlp_config.to_dict(),
        }

    return results


def generate_report(results: dict[str, Any], output_path: Path) -> None:
    """Gera relatório comparativo das variantes."""

    lines = [
        "# Experimento Comparativo de Feature Set",
        "",
        "## Objetivo",
        "",
        "Comparar desempenho do MLP com diferentes configurações de feature set:",
        "- **current**: Feature set atual do contrato ML (5 features)",
        "- **no_deadline**: Feature set atual sem DeadlineMs (4 features)",
        "- **causal_observable**: Features causais observáveis no EdgeSimPy (6 features)",
        "",
        "## Configuração MLP (fixa para todas variantes)",
        "",
        f"- Hidden neurons: {results['variants']['current']['config']['hidden_neurons']}",
        f"- Learning rate: {results['variants']['current']['config']['learning_rate']}",
        f"- Epochs: {results['variants']['current']['config']['epochs']}",
        f"- Seed: {results['variants']['current']['config']['seed']}",
        "",
        "## Dataset",
        "",
        f"- Total: {results['dataset_info']['sizes']['all']}",
        f"- Train: {results['dataset_info']['sizes']['train']}",
        f"- Validation: {results['dataset_info']['sizes']['validation']}",
        f"- Test: {results['dataset_info']['sizes']['test']}",
        f"- Label source: {results['dataset_info']['metadata']['label_source']}",
        "",
        "## Resultados Test Set",
        "",
        format_metrics_table(
            {name: data["test"] for name, data in results["variants"].items()}
        ),
        "",
        "## Resultados Validation Set",
        "",
        format_metrics_table(
            {name: data["validation"] for name, data in results["variants"].items()}
        ),
        "",
        "## Detalhes por Variante",
        "",
    ]

    # Adicionar detalhes por variante
    for variant_name, data in results["variants"].items():
        lines.append(f"### {variant_name}")
        lines.append("")
        lines.append(f"- **Features**: {data['feature_names']}")
        lines.append(f"- **Feature count**: {data['feature_count']}")
        lines.append(f"- **Test Accuracy**: {data['test']['accuracy']:.4f}")
        lines.append(f"- **Test F1 Edge**: {data['test']['f1_edge']:.4f}")
        lines.append(f"- **Test F1 Cloud**: {data['test']['f1_cloud']:.4f}")
        lines.append("")

    # Adicionar confusion matrices
    lines.append("## Confusion Matrices (Test Set)")
    lines.append("")

    for variant_name, data in results["variants"].items():
        cm = data["test"]["confusion_matrix"]
        lines.append(f"### {variant_name}")
        lines.append("")
        lines.append("| | Predicted Edge | Predicted Cloud |")
        lines.append("| --- | ---: | ---: |")
        lines.append(f"| Actual Edge | {cm[0][0]} | {cm[0][1]} |")
        lines.append(f"| Actual Cloud | {cm[1][0]} | {cm[1][1]} |")
        lines.append("")

    # Salvar
    report = "\n".join(lines)
    output_path.write_text(report, encoding="utf-8")

    # Salvar JSON
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\nRelatório salvo: {output_path}")
    print(f"JSON salvo: {json_path}")


def main() -> int:
    """Executa experimento comparativo de feature set."""

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"

    if not dataset_path.exists():
        print(f"Dataset não encontrado: {dataset_path}")
        return 1

    print("Carregando dataset completo...")
    dataset = load_full_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    print(f"Dataset carregado: {dataset.metadata.sample_count} samples")
    print(f"Features completas: {list(FULL_FEATURE_NAMES)}")

    # Preparar dados completos (com todas as features do CSV)
    X_full = np.array(dataset.all_data.X)

    # Criar variantes
    variants = create_feature_variants(X_full, FULL_FEATURE_NAMES)

    # Treinar e comparar
    results = train_and_compare_variants(dataset, variants)

    # Gerar relatório
    results_dir = repository_root / "edgesimpy-simulation" / "results"
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "feature_set_comparison.md"

    generate_report(results, report_path)

    print("\n" + "="*60)
    print("Experimento de feature set concluído!")
    print("="*60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
