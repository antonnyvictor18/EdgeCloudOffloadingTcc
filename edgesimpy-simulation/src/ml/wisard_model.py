"""WiSARD (Weightless Neural Network) implementation for offloading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .dataset import VALID_LABELS
from .preprocessing import WiSARDEncoder


@dataclass(frozen=True)
class WiSARDConfig:
    """Configuration for WiSARD model."""

    bits_per_feature: int = 4
    ram_address_size: int = 8
    seed: int = 7

    def to_dict(self) -> dict[str, Any]:
        return {
            "bits_per_feature": self.bits_per_feature,
            "ram_address_size": self.ram_address_size,
            "seed": self.seed,
        }


class WiSARDDiscriminator:
    """Single discriminator for one class in WiSARD."""

    def __init__(self, mapping: NDArray[np.int_]) -> None:
        self._mapping = mapping
        self._rams: list[set[int]] = [set() for _ in range(len(mapping))]

    def train(self, input_bits: NDArray[np.bool_]) -> None:
        """Train discriminator on one input pattern."""
        for i, positions in enumerate(self._mapping):
            address = self._compute_address(input_bits, positions)
            self._rams[i].add(address)

    def score(self, input_bits: NDArray[np.bool_]) -> int:
        """Score input pattern (number of RAMs that have seen this address)."""
        total = 0
        for i, positions in enumerate(self._mapping):
            address = self._compute_address(input_bits, positions)
            if address in self._rams[i]:
                total += 1
        return total

    @staticmethod
    def _compute_address(input_bits: NDArray[np.bool_], positions: NDArray[np.int_]) -> int:
        """Compute RAM address from input bit positions."""
        address = 0
        for i, pos in enumerate(positions):
            if input_bits[pos]:
                address |= 1 << i
        return address


class WiSARDModel:
    """WiSARD classifier for Edge/Cloud offloading."""

    def __init__(self, config: WiSARDConfig | None = None) -> None:
        self._config = config or WiSARDConfig()
        self._encoder = WiSARDEncoder(bits_per_feature=self._config.bits_per_feature)
        self._discriminators: dict[str, WiSARDDiscriminator] = {}
        self._mapping: NDArray[np.int_] | None = None
        self._is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train WiSARD on feature matrix and labels."""
        if len(X) != len(y):
            raise ValueError("X and y must have same length")

        # Fit encoder on training data
        X_encoded = self._encoder.fit_transform(X)

        # Build random mapping for RAM addresses
        input_length = X_encoded.shape[1]
        self._mapping = self._build_random_mapping(
            input_length, self._config.ram_address_size, self._config.seed
        )

        # Create discriminators for each class
        self._discriminators = {
            label: WiSARDDiscriminator(self._mapping) for label in VALID_LABELS
        }

        # Train each discriminator on its class samples
        for label in VALID_LABELS:
            class_mask = y == label
            class_samples = X_encoded[class_mask]
            for sample in class_samples:
                self._discriminators[label].train(sample)

        self._is_fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels for feature matrix."""
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction")

        X_encoded = self._encoder.transform(X)
        predictions = []

        for sample in X_encoded:
            scores = {
                label: self._discriminators[label].score(sample) for label in VALID_LABELS
            }
            # Tie-break: prefer Edge (consistent with C# implementation)
            predicted = max(scores, key=lambda k: (scores[k], k == "Edge"))
            predictions.append(predicted)

        return np.array(predictions)

    def _build_random_mapping(
        self, input_length: int, address_size: int, seed: int
    ) -> NDArray[np.int_]:
        """Build random mapping from input bits to RAM addresses."""
        rng = np.random.RandomState(seed)
        indices = np.arange(input_length)
        rng.shuffle(indices)

        ram_count = int(np.ceil(input_length / address_size))
        mapping = np.zeros((ram_count, address_size), dtype=int)

        for i in range(ram_count):
            start = i * address_size
            end = min(start + address_size, input_length)
            mapping[i, : end - start] = indices[start:end]

            # Pad if needed
            if end - start < address_size:
                remaining = address_size - (end - start)
                padding = rng.choice(input_length, remaining, replace=False)
                mapping[i, end - start :] = padding

        return mapping

    @property
    def config(self) -> WiSARDConfig:
        """Get model configuration."""
        return self._config

    @property
    def encoder_params(self) -> Any:
        """Get encoder parameters."""
        return self._encoder.params.to_dict() if self._is_fitted else None
