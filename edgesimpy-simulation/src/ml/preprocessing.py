"""Preprocessing for offloading ML models with leakage-aware fitting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizationParams":
        """Create NormalizationParams from dictionary."""
        return cls(
            mins=np.array(data["mins"]),
            maxs=np.array(data["maxs"]),
            feature_names=tuple(data["feature_names"]),
        )


WISARD_ENCODINGS = ("binary", "thermometer")
MAX_BINARY_BITS = 62


@dataclass(frozen=True)
class WiSARDQuantizationParams:
    """Parameters for WiSARD bit quantization fitted on training data."""

    normalization: NormalizationParams
    bits_per_feature: int
    total_bits: int
    encoding: str = "binary"

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalization": self.normalization.to_dict(),
            "bits_per_feature": self.bits_per_feature,
            "total_bits": self.total_bits,
            "encoding": self.encoding,
        }


class MinMaxNormalizer:
    """Min-max normalization fitted only on training data."""

    def __init__(self) -> None:
        self._params: NormalizationParams | None = None

    def fit(self, X: np.ndarray) -> None:
        """Fit normalization parameters on training data."""
        if X.shape[1] < 1:
            raise ValueError("X must have at least 1 feature")

        mins = X.min(axis=0)
        maxs = X.max(axis=0)

        # Avoid division by zero for constant features
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0

        self._params = NormalizationParams(
            mins=mins,
            maxs=maxs,
            feature_names=tuple(f"feature_{i}" for i in range(X.shape[1])),
        )

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Apply normalization using fitted parameters."""
        if self._params is None:
            raise ValueError("Normalizer must be fitted before transform")

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
    """Encode features for WiSARD using quantization to bits.

    Encodings (per feature, after min-max normalization fitted on train):
    - "binary": positional binary code of the quantized level in
      [0, 2^bits - 1]. Mirrors the C# WisardStrategy. Adjacent levels can
      differ in many bits (7=0111 vs 8=1000), which weakens the address
      locality WiSARD relies on for generalization.
    - "thermometer": unary code - level k in [0, bits] turns on the first k
      bits. Adjacent levels always differ by exactly one bit (canonical
      WiSARD input encoding). Resolution is bits + 1 levels.
    """

    def __init__(self, bits_per_feature: int = 4, encoding: str = "binary") -> None:
        if encoding not in WISARD_ENCODINGS:
            raise ValueError(f"encoding must be one of {WISARD_ENCODINGS}, got {encoding!r}")
        if bits_per_feature < 1:
            raise ValueError("bits_per_feature must be >= 1")
        if encoding == "binary" and bits_per_feature > MAX_BINARY_BITS:
            # Quantized level 2^bits - 1 must fit in int64 without overflow
            raise ValueError(
                f"binary encoding supports at most {MAX_BINARY_BITS} bits per feature "
                f"(int64 level range), got {bits_per_feature}"
            )
        self.bits_per_feature = bits_per_feature
        self.encoding = encoding
        self._normalizer = MinMaxNormalizer()
        self._params: WiSARDQuantizationParams | None = None

    def fit(self, X: np.ndarray) -> None:
        """Fit quantization parameters on training data."""
        self._normalizer.fit(X)
        self._params = WiSARDQuantizationParams(
            normalization=self._normalizer.params,
            bits_per_feature=self.bits_per_feature,
            total_bits=X.shape[1] * self.bits_per_feature,
            encoding=self.encoding,
        )

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform features to binary representation for WiSARD."""
        if self._params is None:
            raise ValueError("Encoder must be fitted before transform")

        normalized = self._normalizer.transform(X)
        n_samples, n_features = normalized.shape
        nb = self.bits_per_feature

        if self.encoding == "thermometer":
            levels = np.round(normalized * nb).astype(int)  # [0, nb]
            # bit b of feature i is on iff b < level_i
            bits = np.arange(nb)[None, None, :] < levels[:, :, None]
            return bits.reshape(n_samples, n_features * nb)

        # Quantize each feature to bits_per_feature bits
        max_level = (1 << nb) - 1
        quantized = np.round(normalized * max_level).astype(np.int64)

        # Convert to binary representation
        bits = np.zeros((n_samples, n_features * nb), dtype=bool)
        for i in range(n_features):
            for b in range(nb):
                bits[:, i * nb + b] = (quantized[:, i] >> b) & 1 == 1

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
