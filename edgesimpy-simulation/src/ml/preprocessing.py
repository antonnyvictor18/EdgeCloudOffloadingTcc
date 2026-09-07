"""Preprocessing for offloading ML models with leakage-aware fitting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .dataset import FEATURE_NAMES


@dataclass(frozen=True)
class NormalizationParams:
    """Parameters for min-max normalization fitted on training data."""

    mins: np.ndarray
    maxs: np.ndarray
    feature_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_names": list(self.feature_names),
            "mins": self.mins.tolist(),
            "maxs": self.maxs.tolist(),
        }


@dataclass(frozen=True)
class WiSARDQuantizationParams:
    """Parameters for WiSARD bit quantization fitted on training data."""

    normalization: NormalizationParams
    bits_per_feature: int
    total_bits: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalization": self.normalization.to_dict(),
            "bits_per_feature": self.bits_per_feature,
            "total_bits": self.total_bits,
        }


class MinMaxNormalizer:
    """Min-max normalization fitted only on training data."""

    def __init__(self) -> None:
        self._params: NormalizationParams | None = None

    def fit(self, X: np.ndarray) -> None:
        """Fit normalization parameters on training data."""
        if X.shape[1] != len(FEATURE_NAMES):
            raise ValueError(f"Expected {len(FEATURE_NAMES)} features, got {X.shape[1]}")

        mins = X.min(axis=0)
        maxs = X.max(axis=0)

        # Avoid division by zero for constant features
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0

        self._params = NormalizationParams(
            mins=mins,
            maxs=maxs,
            feature_names=FEATURE_NAMES,
        )

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Apply normalization using fitted parameters."""
        if self._params is None:
            raise ValueError("Normalizer must be fitted before transform")

        if X.shape[1] != len(self._params.feature_names):
            raise ValueError(
                f"Expected {len(self._params.feature_names)} features, got {X.shape[1]}"
            )

        normalized = (X - self._params.mins) / (self._params.maxs - self._params.mins)
        return np.clip(normalized, 0.0, 1.0)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit and transform in one call (for training data only)."""
        self.fit(X)
        return self.transform(X)

    @property
    def params(self) -> NormalizationParams:
        """Get fitted parameters."""
        if self._params is None:
            raise ValueError("Normalizer not fitted")
        return self._params


class WiSARDEncoder:
    """Encode features for WiSARD using quantization to bits."""

    def __init__(self, bits_per_feature: int = 4) -> None:
        self.bits_per_feature = bits_per_feature
        self._normalizer = MinMaxNormalizer()
        self._params: WiSARDQuantizationParams | None = None

    def fit(self, X: np.ndarray) -> None:
        """Fit quantization parameters on training data."""
        self._normalizer.fit(X)
        self._params = WiSARDQuantizationParams(
            normalization=self._normalizer.params,
            bits_per_feature=self.bits_per_feature,
            total_bits=X.shape[1] * self.bits_per_feature,
        )

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform features to binary representation for WiSARD."""
        if self._params is None:
            raise ValueError("Encoder must be fitted before transform")

        normalized = self._normalizer.transform(X)
        n_samples, n_features = normalized.shape

        # Quantize each feature to bits_per_feature bits
        max_level = (1 << self.bits_per_feature) - 1
        quantized = np.round(normalized * max_level).astype(int)

        # Convert to binary representation
        bits = np.zeros((n_samples, n_features * self.bits_per_feature), dtype=bool)
        for i in range(n_features):
            for b in range(self.bits_per_feature):
                bits[:, i * self.bits_per_feature + b] = (quantized[:, i] >> b) & 1 == 1

        return bits

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit and transform in one call (for training data only)."""
        self.fit(X)
        return self.transform(X)

    @property
    def params(self) -> WiSARDQuantizationParams:
        """Get fitted parameters."""
        if self._params is None:
            raise ValueError("Encoder not fitted")
        return self._params
