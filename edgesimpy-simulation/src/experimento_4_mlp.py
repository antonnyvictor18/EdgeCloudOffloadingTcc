"""Experimento comparativo de 4 MLPs com diferentes feature sets.

Comparacao controlada:
- MLP_current: 5 features (contrato atual)
- MLP_no_deadline: 4 features (sem DeadlineMs)
- MLP_causal_observable_7: 7 features (com DeadlineMs + Bandwidth + NetworkLatency)
- MLP_final_6: 6 features (sem DeadlineMs, com Bandwidth + NetworkLatency)

Objetivo: separar efeito de DeadlineMs de efeito de BandwidthMbps + NetworkLatencyMs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ml.dataset_full import load_full_offloading_dataset
from ml.mlp_model import MLPConfig, MLPModel
from ml.metrics import compute_metrics


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


@dataclass(frozen=True)
class MLPVariant:
    """Configuracao de uma variante de MLP."""

    name: str
    features: tuple[str, ...]
    description: str


def create_mlp_variants() -> list[MLPVariant]:
    """Cria as 4 variantes de MLP para comparacao."""

    return [
        MLPVariant(
            name="MLP_current",
            features=(
                "CpuCycles",
                "TaskSizeMB",
                "DeadlineMs",
                "LatencySensitivity",
                "RequiredMemoryMB",
            ),
            description="Contrato ML atual (5 features)",
        ),
        MLPVariant(
            name="MLP_no_deadline",
            features=(
                "CpuCycles",
                "TaskSizeMB",
                "LatencySensitivity",
                "RequiredMemoryMB",
            ),
            description="Contrato atual sem DeadlineMs (4 features)",
        ),
        MLPVariant(
            name="MLP_causal_observable_7",
            features=(
                "CpuCycles",
                "TaskSizeMB",
                "DeadlineMs",
                "LatencySensitivity",
                "RequiredMemoryMB",
                "BandwidthMbps",
                "NetworkLatencyMs",
            ),
            description="Features causais observaveis com DeadlineMs (7 features)",
        ),
        MLPVariant(
            name="MLP_final_6",
            features=(
                "CpuCycles",
                "TaskSizeMB",
                "LatencySensitivity",
                "RequiredMemoryMB",
                "BandwidthMbps",
                "NetworkLatencyMs",
            ),
            description="Feature set final - causal sem DeadlineMs (6 features)",
        ),
    ]


def prepare_variant_data(
    X_full: np.ndarray,
    variant_features: tuple[str, ...],
    full_feature_names: tuple[str, ...],
) -> np.ndarray:
    """Prepara dados para uma variante selecionando colunas."""
    variant_indices = [
        i for i, name in enumerate(full_feature_names) if name in variant_features
    ]
    return X_full[:, variant_indices]


def train_and_compare_mlp_variants(
    dataset,
    variants: list[MLPVariant],
) -> dict[str, Any]:
    """Treina e compara todas as variantes de MLP."""

    results = {
        "dataset_info": dataset.to_dict(),
        "variants": {},
    }

    # Configuracao MLP fixa
    mlp_config = MLPConfig(hidden_neurons=18, learning_rate=0.04, epochs=35, seed=11)

    # Preparar dados completos
    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_val = np.array(dataset.validation.X)
    y_val = np.array(dataset.validation.y)
    X_test = np.array(dataset.test.X)
    y_test = np.array(dataset.test.y)

    for variant in variants:
        print(f"\n{'='*70}")
        print(f"Treinando: {variant.name}")
        print(f"Descricao: {variant.description}")
        print(f"Features: {list(variant.features)}")
        print(f"Feature count: {len(variant.features)}")
        print(f"{'='*70}")

        # Preparar dados para esta variante
        X_train_variant = prepare_variant_data(X_train, variant.features, FULL_FEATURE_NAMES)
        X_val_variant = prepare_variant_data(X_val, variant.features, FULL_FEATURE_NAMES)
        X_test_variant = prepare_variant_data(X_test, variant.features, FULL_FEATURE_NAMES)

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
        results["variants"][variant.name] = {
            "description": variant.description,
            "feature_names": list(variant.features),
            "feature_count": len(variant.features),
            "validation": val_metrics.to_dict(),
            "test": test_metrics.to_dict(),
            "config": mlp_config.to_dict(),
        }

    return results


def generate_markdown_report(results: dict[str, Any], output_path: Path) -> None:
    """Gera relatorio em Markdown com comparacao das 4 variantes."""

    lines = [
        "# Experimento Comparativo de 4 MLPs",
        "",
        "## Objetivo",
        "",
        "Comparar 4 variantes de MLP com diferentes feature sets:",
        "",
        "- **MLP_current**: Contrato ML atual (5 features)",
        "- **MLP_no_deadline**: Contrato atual sem DeadlineMs (4 features)",
        "- **MLP_causal_observable_7**: Features causais observaveis com DeadlineMs (7 features)",
        "- **MLP_final_6**: Feature set final - causal sem DeadlineMs (6 features)",
        "",
        "## Configuracao MLP (fixa para todas variantes)",
        "",
        "- Hidden neurons: 18",
        "- Learning rate: 0.04",
        "- Epochs: 35",
        "- Seed: 11",
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
        "| Modelo                   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |",
        "| ------------------------ | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |",
    ]

    # Adicionar tabela ordenada por accuracy descendente
    variant_results = sorted(
        results["variants"].items(),
        key=lambda x: x[1]["test"]["accuracy"],
        reverse=True,
    )

    for name, variant in variant_results:
        test = variant["test"]
        lines.append(
            f"| {name:24} | {test['accuracy']:.4f} | {test['precision_edge']:.4f} | {test['recall_edge']:.4f} | {test['f1_edge']:.4f} | {test['precision_cloud']:.4f} | {test['recall_cloud']:.4f} | {test['f1_cloud']:.4f} |"
        )

    lines.extend([
        "",
        "## Resultados Validation Set",
        "",
        "| Modelo                   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |",
        "| ------------------------ | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |",
    ])

    # Adicionar tabela validation ordenada
    variant_results_val = sorted(
        results["variants"].items(),
        key=lambda x: x[1]["validation"]["accuracy"],
        reverse=True,
    )

    for name, variant in variant_results_val:
        val = variant["validation"]
        lines.append(
            f"| {name:24} | {val['accuracy']:.4f} | {val['precision_edge']:.4f} | {val['recall_edge']:.4f} | {val['f1_edge']:.4f} | {val['precision_cloud']:.4f} | {val['recall_cloud']:.4f} | {val['f1_cloud']:.4f} |"
        )

    lines.extend([
        "",
        "## Detalhes por Variante",
        "",
    ])

    for name, variant in results["variants"].items():
        lines.extend([
            f"### {name}",
            "",
            f"- **Descricao**: {variant['description']}",
            f"- **Features**: {variant['feature_names']}",
            f"- **Feature count**: {variant['feature_count']}",
            f"- **Test Accuracy**: {variant['test']['accuracy']:.4f}",
            f"- **Test F1 Edge**: {variant['test']['f1_edge']:.4f}",
            f"- **Test F1 Cloud**: {variant['test']['f1_cloud']:.4f}",
            "",
        ])

    lines.extend([
        "## Confusion Matrices (Test Set)",
        "",
    ])

    for name, variant in results["variants"].items():
        cm = variant["test"]["confusion_matrix"]
        # cm is [[TN_edge, FP_cloud], [FN_edge, TP_cloud]]
        lines.extend([
            f"### {name}",
            "",
            "|                | Predicted Edge | Predicted Cloud |",
            "| -------------- | -------------: | ---------------: |",
            f"| Actual Edge    | {cm[0][0]:<14} | {cm[0][1]:<15} |",
            f"| Actual Cloud   | {cm[1][0]:<14} | {cm[1][1]:<15} |",
            "",
        ])

    lines.extend([
        "## Distribuicao de Previsoes (Test Set)",
        "",
    ])

    for name, variant in results["variants"].items():
        pred_dist = variant["test"]["prediction_distribution"]
        total = sum(pred_dist.values())
        predicted_edge = pred_dist.get("Edge", 0)
        predicted_cloud = pred_dist.get("Cloud", 0)

        lines.extend([
            f"### {name}",
            "",
            f"- Predicted Edge: {predicted_edge} ({predicted_edge/total:.1%})",
            f"- Predicted Cloud: {predicted_cloud} ({predicted_cloud/total:.1%})",
            "",
        ])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Relatorio salvo: {output_path}")


def main() -> int:
    """Executa experimento comparativo de 4 MLPs."""

    repository_root = Path(__file__).resolve().parents[2]
    dataset_path = repository_root / "Dataset" / "dataset.csv"

    if not dataset_path.exists():
        print(f"Dataset não encontrado: {dataset_path}")
        return 1

    print("Carregando dataset completo...")
    dataset = load_full_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    print(f"Dataset carregado: {dataset.metadata.sample_count} samples")
    print(f"Features completas: {list(FULL_FEATURE_NAMES)}")

    # Criar variantes
    variants = create_mlp_variants()

    print(f"\n{len(variants)} variantes de MLP configuradas")

    # Treinar e comparar
    results = train_and_compare_mlp_variants(dataset, variants)

    # Gerar relatorio
    results_dir = repository_root / "edgesimpy-simulation" / "results"
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "mlp_4_variants_comparison.md"

    generate_markdown_report(results, report_path)

    # Salvar JSON
    import json
    json_path = results_dir / "mlp_4_variants_comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"JSON salvo: {json_path}")

    print("\n" + "="*70)
    print("Experimento comparativo de 4 MLPs concluido!")
    print("="*70)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
