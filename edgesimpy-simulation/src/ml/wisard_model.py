"""WiSARD (Weightless Neural Network) implementation for offloading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .dataset import VALID_LABELS
from .preprocessing import WiSARDEncoder

# Deterministic class order for vectorized scoring
CLASS_ORDER: tuple[str, ...] = tuple(sorted(VALID_LABELS))  # ("Cloud", "Edge")


@dataclass(frozen=True)
class WiSARDConfig:
    """Configuration for WiSARD model.

    Defaults reproduce the C# WisardStrategy (binary encoding, 4 bits,
    8-bit RAM addresses, seed 7, no bleaching, ties -> Edge).

    bleaching: when True, RAMs store write counts and a tie between class
    scores is resolved by raising the activation threshold b (score = number
    of RAMs whose count >= b) until the tie breaks or all scores reach zero.
    Residual ties still fall back to Edge (C# convention).
    """

    bits_per_feature: int = 4
    ram_address_size: int = 8
    seed: int = 7
    encoding: str = "binary"
    bleaching: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "bits_per_feature": self.bits_per_feature,
            "ram_address_size": self.ram_address_size,
            "seed": self.seed,
            "encoding": self.encoding,
            "bleaching": self.bleaching,
        }


# C# WisardStrategy-equivalent configuration (reference baseline). On the
# 6-feature contract it collapses to ~all-Edge (validation macro-F1 0.395,
# tie rate ~84%).
WISARD_CSHARP_EQUIVALENT = WiSARDConfig(
    bits_per_feature=4, ram_address_size=8, seed=7, encoding="binary", bleaching=False
)

# Frozen configuration selected by experimento_tuning_wisard.py (validation
# macro-F1, 5 mapping seeds, test split untouched). Validation (mean of 5
# seeds, canonical split): macro-F1 0.738 +- 0.009, accuracy 0.768, recall
# Cloud 0.576. Sits on a plateau with thermometer/addr=16/bleaching at 8-32
# bits (within ~1 sd); selected per the pre-registered rule (highest mean).
# Final test (seed 7): accuracy 0.747, macro-F1 0.718 (final_test_evaluation.md).
WISARD_FINAL_6 = WiSARDConfig(
    bits_per_feature=64, ram_address_size=16, seed=7, encoding="thermometer", bleaching=True
)


class WiSARDDiscriminator:
    """Single discriminator for one class in WiSARD.

    RAM contents are stored as write counts in a dense (ram_count, 2^n)
    array so scoring is vectorized. Without bleaching, a RAM "has seen" an
    address iff its count >= 1 (identical to the set-based C# semantics).
    """

    def __init__(self, mapping: NDArray[np.int_]) -> None:
        self._mapping = mapping
        ram_count, address_size = mapping.shape
        self._counts = np.zeros((ram_count, 1 << address_size), dtype=np.int32)
        self._ram_index = np.arange(ram_count)

    def train_batch(self, addresses: NDArray[np.int_]) -> None:
        """Train on a batch of pre-computed RAM addresses (n, ram_count)."""
        for row in addresses:
            self._counts[self._ram_index, row] += 1

    def train(self, input_bits: NDArray[np.bool_]) -> None:
        """Train discriminator on one input pattern."""
        self.train_batch(compute_addresses(input_bits[None, :], self._mapping))

    def counts(self, addresses: NDArray[np.int_]) -> NDArray[np.int_]:
        """Per-RAM write counts at the given addresses -> (n, ram_count)."""
        return self._counts[self._ram_index[None, :], addresses]

    def score(self, input_bits: NDArray[np.bool_], threshold: int = 1) -> int:
        """Score one input pattern (number of RAMs with count >= threshold)."""
        addresses = compute_addresses(input_bits[None, :], self._mapping)
        return int((self.counts(addresses)[0] >= threshold).sum())

    @property
    def ram_count(self) -> int:
        return self._counts.shape[0]

    @property
    def stored_addresses(self) -> int:
        """Number of distinct (RAM, address) cells written (memory proxy)."""
        return int((self._counts > 0).sum())


def compute_addresses(input_bits: NDArray[np.bool_], mapping: NDArray[np.int_]) -> NDArray[np.int_]:
    """Compute RAM addresses for a batch: (n, total_bits) -> (n, ram_count).

    Bit i of the tuple (positions[i]) contributes 1 << i, matching the C#
    Address() implementation.
    """
    tuple_bits = input_bits[:, mapping]  # (n, ram_count, address_size)
    weights = (1 << np.arange(mapping.shape[1], dtype=np.int64))
    return (tuple_bits.astype(np.int64) * weights).sum(axis=2)


class WiSARDModel:
    """WiSARD classifier for Edge/Cloud offloading."""

    def __init__(self, config: WiSARDConfig | None = None) -> None:
        self._config = config or WiSARDConfig()
        self._encoder = WiSARDEncoder(
            bits_per_feature=self._config.bits_per_feature,
            encoding=self._config.encoding,
        )
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
            label: WiSARDDiscriminator(self._mapping) for label in CLASS_ORDER
        }

        # Train each discriminator on its class samples
        addresses = compute_addresses(X_encoded, self._mapping)
        y = np.asarray(y)
        for label in CLASS_ORDER:
            self._discriminators[label].train_batch(addresses[y == label])

        self._is_fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels for feature matrix."""
        return np.array([s["prediction"] for s in self.scores(X)])

    def scores(self, X: np.ndarray) -> list[dict[str, Any]]:
        """Per-sample decision evidence.

        Returns one dict per sample with keys: one entry per class with the
        discriminator score at the final threshold, "threshold" (bleaching
        level used; 1 when bleaching is off), "tie" (whether the final
        decision was a residual tie resolved to Edge) and "prediction".
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction")

        X_encoded = self._encoder.transform(X)
        addresses = compute_addresses(X_encoded, self._mapping)
        # (n_classes, n, ram_count)
        counts = np.stack(
            [self._discriminators[label].counts(addresses) for label in CLASS_ORDER]
        )
        n = counts.shape[1]
        threshold = np.ones(n, dtype=np.int64)
        scores = (counts >= threshold[None, :, None]).sum(axis=2)  # (n_classes, n)

        if self._config.bleaching:
            tied = _tied(scores) & (scores.max(axis=0) > 0)
            while tied.any():
                threshold[tied] += 1
                scores[:, tied] = (counts[:, tied] >= threshold[None, tied, None]).sum(axis=2)
                tied = _tied(scores) & (scores.max(axis=0) > 0)

        residual_tie = _tied(scores)
        # Tie-break: prefer Edge (consistent with C# implementation)
        edge_idx = CLASS_ORDER.index("Edge")
        best = scores.argmax(axis=0)
        best[residual_tie] = edge_idx

        return [
            {
                **{label: int(scores[c, i]) for c, label in enumerate(CLASS_ORDER)},
                "threshold": int(threshold[i]),
                "tie": bool(residual_tie[i]),
                "prediction": CLASS_ORDER[best[i]],
            }
            for i in range(n)
        ]

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

    @property
    def ram_count(self) -> int:
        if self._mapping is None:
            raise ValueError("Model not fitted")
        return int(self._mapping.shape[0])

    @property
    def stored_addresses(self) -> int:
        """Total distinct RAM cells written across discriminators (memory proxy)."""
        return sum(d.stored_addresses for d in self._discriminators.values())


def _tied(scores: NDArray[np.int_]) -> NDArray[np.bool_]:
    """True where the top two class scores are equal (binary: all equal)."""
    top = np.sort(scores, axis=0)
    return top[-1] == top[-2]
