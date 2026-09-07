"""Training protocol for offloading ML models with leakage-aware evaluation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.baseline import MajorityClassifier
from ml.dataset import FEATURE_NAMES, PreparedDataset, load_offloading_dataset
from ml.metrics import ClassificationMetrics, compute_metrics, format_config_table, format_metrics_table
from ml.mlp_model import MLPConfig, MLPModel
from ml.wisard_model import WiSARDConfig, WiSARDModel


def train_and_evaluate(dataset: PreparedDataset) -> dict[str, Any]:
    """Train all models and evaluate them on test set."""

    # Convert to numpy arrays
    X_train = np.array(dataset.train.X)
    y_train = np.array(dataset.train.y)
    X_val = np.array(dataset.validation.X)
    y_val = np.array(dataset.validation.y)
    X_test = np.array(dataset.test.X)
    y_test = np.array(dataset.test.y)

    results: dict[str, Any] = {
        "dataset_info": dataset.to_dict(),
        "models": {},
        "configurations": {},
    }

    # Train and evaluate each model
    models_to_train = [
        ("Majority", MajorityClassifier(), {"seed": None, "preprocessing": "none", "hyperparameters": {}}),
        ("WiSARD", WiSARDModel(WiSARDConfig()), WiSARDConfig().to_dict()),
        ("MLP", MLPModel(MLPConfig()), MLPConfig().to_dict()),
    ]

    for model_name, model, config in models_to_train:
        print(f"\n{'='*60}")
        print(f"Training {model_name}")
        print(f"{'='*60}")

        # TRAIN phase
        print(f"Training on {len(X_train)} samples...")
        model.fit(X_train, y_train)
        print(f"Training complete.")

        # Store configuration
        model_config = {
            "seed": config.get("seed"),
            "preprocessing": config.get("preprocessing", "min-max normalization"),
            "hyperparameters": config.get("hyperparameters", config),
        }

        # Add preprocessing params if available
        if hasattr(model, "encoder_params") and model.encoder_params:
            model_config["preprocessing_params"] = model.encoder_params
        elif hasattr(model, "normalizer_params") and model.normalizer_params:
            model_config["preprocessing_params"] = model.normalizer_params

        results["configurations"][model_name] = model_config

        # VALIDATION phase
        print(f"Validating on {len(X_val)} samples...")
        y_val_pred = model.predict(X_val)
        val_metrics = compute_metrics(y_val, y_val_pred)
        print(f"Validation Accuracy: {val_metrics.accuracy:.4f}")
        print(f"Validation F1 Edge: {val_metrics.f1_edge:.4f}")
        print(f"Validation F1 Cloud: {val_metrics.f1_cloud:.4f}")

        # TEST phase (final evaluation)
        print(f"Testing on {len(X_test)} samples...")
        y_test_pred = model.predict(X_test)
        test_metrics = compute_metrics(y_test, y_test_pred)
        print(f"Test Accuracy: {test_metrics.accuracy:.4f}")
        print(f"Test F1 Edge: {test_metrics.f1_edge:.4f}")
        print(f"Test F1 Cloud: {test_metrics.f1_cloud:.4f}")

        # Store results
        results["models"][model_name] = {
            "validation": val_metrics.to_dict(),
            "test": test_metrics.to_dict(),
        }

    return results


def generate_report(results: dict[str, Any], output_path: Path) -> None:
    """Generate markdown report with results."""

    lines = [
        "# ML Models Training Report",
        "",
        "## Dataset Information",
        "",
        f"- **Version**: {results['dataset_info']['metadata']['dataset_version']}",
        f"- **Source**: {results['dataset_info']['metadata']['source_path']}",
        f"- **Source Seed**: {results['dataset_info']['metadata']['source_seed']}",
        f"- **Split Seed**: {results['dataset_info']['metadata']['split_seed']}",
        f"- **Label Source**: {results['dataset_info']['metadata']['label_source']}",
        f"- **Total Samples**: {results['dataset_info']['sizes']['all']}",
        f"- **Train**: {results['dataset_info']['sizes']['train']}",
        f"- **Validation**: {results['dataset_info']['sizes']['validation']}",
        f"- **Test**: {results['dataset_info']['sizes']['test']}",
        "",
        "### Class Distribution",
        "",
        f"- **All**: {results['dataset_info']['class_counts']['all']}",
        f"- **Train**: {results['dataset_info']['class_counts']['train']}",
        f"- **Validation**: {results['dataset_info']['class_counts']['validation']}",
        f"- **Test**: {results['dataset_info']['class_counts']['test']}",
        "",
        "### Features",
        "",
        f"- **Feature Names**: {results['dataset_info']['metadata']['feature_names']}",
        f"- **Omitted Features**: {results['dataset_info']['metadata']['omitted_features'][:2]} (and more)",
        "",
        "## Model Configurations",
        "",
        format_config_table(results["configurations"]),
        "",
        "## Test Set Results",
        "",
        format_metrics_table(
            {name: data["test"] for name, data in results["models"].items()}
        ),
        "",
        "## Validation Set Results",
        "",
        format_metrics_table(
            {name: data["validation"] for name, data in results["models"].items()}
        ),
        "",
        "## Confusion Matrices (Test Set)",
        "",
    ]

    # Add confusion matrices
    for model_name, model_data in results["models"].items():
        cm = model_data["test"]["confusion_matrix"]
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| | Predicted Edge | Predicted Cloud |")
        lines.append("| --- | ---: | ---: |")
        lines.append(f"| Actual Edge | {cm[0][0]} | {cm[0][1]} |")
        lines.append(f"| Actual Cloud | {cm[1][0]} | {cm[1][1]} |")
        lines.append("")

    # Add prediction distributions
    lines.append("## Prediction Distributions (Test Set)")
    lines.append("")
    for model_name, model_data in results["models"].items():
        dist = model_data["test"]["prediction_distribution"]
        lines.append(f"- **{model_name}**: {dist}")
    lines.append("")

    # Add circularity warning
    lines.append("## Methodological Limitations")
    lines.append("")
    lines.append("**IMPORTANT**: The labels in this dataset were generated by the C# analytical simulator.")
    lines.append("This creates a circularity issue: the models are learning to reproduce the analytical")
    lines.append("formula, not generalizing to real-world scenarios. High accuracy should be interpreted")
    lines.append("as \"the model learned the analytical formula well\" rather than \"the model is intelligent\".")
    lines.append("")
    lines.append("## Files Generated")
    lines.append("")
    lines.append(f"- This report: {output_path}")
    lines.append(f"- Full JSON results: {output_path.with_suffix('.json')}")

    report = "\n".join(lines)
    output_path.write_text(report, encoding="utf-8")

    # Also save JSON
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\nReport saved to: {output_path}")
    print(f"JSON results saved to: {json_path}")


def main() -> int:
    """Main training entry point."""
    repository_root = Path(__file__).resolve().parents[3]
    dataset_path = repository_root / "Dataset" / "dataset.csv"

    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return 1

    print(f"Loading dataset from: {dataset_path}")
    dataset = load_offloading_dataset(dataset_path, source_seed=42, split_seed=43)

    print(f"Dataset loaded: {dataset.metadata.sample_count} samples")
    print(f"Features: {list(FEATURE_NAMES)}")
    print(f"Train: {len(dataset.train.y)}, Validation: {len(dataset.validation.y)}, Test: {len(dataset.test.y)}")

    # Train and evaluate
    results = train_and_evaluate(dataset)

    # Generate report
    results_dir = repository_root / "edgesimpy-simulation" / "results"
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "ml_models_report.md"

    generate_report(results, report_path)

    print("\n" + "="*60)
    print("Training and evaluation complete!")
    print("="*60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
