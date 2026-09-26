"""MLP (Multi-Layer Perceptron) implementation for offloading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .dataset import VALID_LABELS
from .preprocessing import MinMaxNormalizer, NormalizationParams


@dataclass(frozen=True)
class MLPConfig:
    """Configuration for MLP model."""

    hidden_neurons: int = 18
    learning_rate: float = 0.04
    epochs: int = 35
    seed: int = 11

    def to_dict(self) -> dict[str, Any]:
        return {
            "hidden_neurons": self.hidden_neurons,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "seed": self.seed,
        }


class MLPModel:
    """Multi-Layer Perceptron classifier for Edge/Cloud offloading."""

    def __init__(self, config: MLPConfig | None = None) -> None:
        self._config = config or MLPConfig()
        self._normalizer = MinMaxNormalizer()
        self._rng = np.random.RandomState(self._config.seed)

        # Network parameters
        self._w1: NDArray[np.float64] | None = None  # Input -> Hidden
        self._b1: NDArray[np.float64] | None = None  # Hidden bias
        self._w2: NDArray[np.float64] | None = None  # Hidden -> Output
        self._b2: float = 0.0  # Output bias

        self._is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train MLP on feature matrix and labels."""
        if len(X) != len(y):
            raise ValueError("X and y must have same length")

        # Fit normalizer on training data
        X_normalized = self._normalizer.fit_transform(X)

        # Initialize network
        n_input = X.shape[1]
        n_hidden = self._config.hidden_neurons

        self._w1 = self._xavier_init(n_input, n_hidden)
        self._b1 = np.zeros(n_hidden)
        self._w2 = self._xavier_init(n_hidden, 1).flatten()
        self._b2 = 0.0

        # Convert labels to binary (Cloud=1, Edge=0)
        y_binary = (y == "Cloud").astype(float)

        # Training loop
        for epoch in range(self._config.epochs):
            # Shuffle samples each epoch
            indices = self._rng.permutation(len(X_normalized))
            X_shuffled = X_normalized[indices]
            y_shuffled = y_binary[indices]

            for x_sample, y_sample in zip(X_shuffled, y_shuffled):
                self._train_one(x_sample, y_sample)

        self._is_fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels for feature matrix."""
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction")

        X_normalized = self._normalizer.transform(X)
        predictions = []

        for x_sample in X_normalized:
            _, output = self._forward(x_sample)
            # Output >= 0.5 means Cloud (consistent with C# implementation)
            predicted = "Cloud" if output >= 0.5 else "Edge"
            predictions.append(predicted)

        return np.array(predictions)

    def _train_one(self, x: NDArray[np.float64], y: float) -> None:
        """Train on a single sample using backpropagation."""
        if self._w1 is None or self._b1 is None or self._w2 is None:
            raise ValueError("Network not initialized")

        # Forward pass
        hidden, output = self._forward(x)

        # Backward pass
        output_delta = output - y
        w2_previous = self._w2.copy()

        # Update output layer
        grad_w2 = output_delta * hidden
        self._w2 -= self._config.learning_rate * grad_w2
        self._b2 -= self._config.learning_rate * output_delta

        # Update hidden layer
        for h in range(len(hidden)):
            hidden_delta = output_delta * w2_previous[h] * hidden[h] * (1 - hidden[h])
            grad_w1 = hidden_delta * x
            self._w1[:, h] -= self._config.learning_rate * grad_w1
            self._b1[h] -= self._config.learning_rate * hidden_delta

    def _forward(self, x: NDArray[np.float64]) -> tuple[NDArray[np.float64], float]:
        """Forward pass through network."""
        if self._w1 is None or self._b1 is None or self._w2 is None:
            raise ValueError("Network not initialized")

        # Hidden layer
        hidden_sum = self._b1 + x @ self._w1
        hidden = self._sigmoid(hidden_sum)

        # Output layer
        output_sum = self._b2 + hidden @ self._w2
        output = self._sigmoid(output_sum)

        return hidden, float(output)

    @staticmethod
    def _sigmoid(x: NDArray[np.float64] | float) -> NDArray[np.float64] | float:
        """Sigmoid activation function with numerical stability."""
        # Clamp to avoid overflow
        x_clamped = np.clip(x, -35, 35)
        return 1.0 / (1.0 + np.exp(-x_clamped))

    def _xavier_init(self, fan_in: int, fan_out: int) -> NDArray[np.float64]:
        """Xavier/Glorot initialization."""
        scale = np.sqrt(1.0 / fan_in)
        return self._rng.uniform(-scale, scale, size=(fan_in, fan_out))

    @property
    def config(self) -> MLPConfig:
        """Get model configuration."""
        return self._config

    @property
    def normalizer(self) -> MinMaxNormalizer:
        """Get the normalizer instance."""
        return self._normalizer

    @property
    def normalizer_params(self) -> Any:
        """Get normalizer parameters."""
        return self._normalizer.params.to_dict() if self._is_fitted else None

    def save(self, path: Path) -> None:
        """Save model weights and normalizer parameters to disk.

        Args:
            path: Path to save the model (without extension)
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before saving")

        import json

        model_dir = path.parent
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save weights as numpy arrays
        weights_path = path.with_suffix(".npz")
        np.savez(
            weights_path,
            w1=self._w1,
            b1=self._b1,
            w2=self._w2,
            b2=self._b2,
        )

        # Save config and normalizer params as JSON
        metadata = {
            "config": self._config.to_dict(),
            "normalizer_params": self.normalizer_params,
            "is_fitted": self._is_fitted,
        }

        metadata_path = path.with_suffix(".json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def load(self, path: Path) -> None:
        """Load model weights and normalizer parameters from disk.

        Args:
            path: Path to load the model from (without extension)
        """
        import json

        # Load metadata
        metadata_path = path.with_suffix(".json")
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Load weights
        weights_path = path.with_suffix(".npz")
        weights = np.load(weights_path)

        self._w1 = weights["w1"]
        self._b1 = weights["b1"]
        self._w2 = weights["w2"]
        self._b2 = float(weights["b2"])

        # Restore normalizer params
        normalizer_params_dict = metadata["normalizer_params"]
        self._normalizer._params = NormalizationParams.from_dict(normalizer_params_dict)

        self._is_fitted = metadata["is_fitted"]
