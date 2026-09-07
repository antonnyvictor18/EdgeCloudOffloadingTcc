"""Simple baseline classifiers for comparison."""

from __future__ import annotations

from collections import Counter

import numpy as np


class MajorityClassifier:
    """Always predicts the majority class from training data."""

    def __init__(self) -> None:
        self._majority_class: str | None = None
        self._is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit by finding majority class in training data."""
        # X is ignored for this baseline
        counter = Counter(y)
        self._majority_class = counter.most_common(1)[0][0]
        self._is_fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict majority class for all samples."""
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction")

        if self._majority_class is None:
            raise ValueError("Model not fitted properly")

        return np.full(len(X), self._majority_class)

    @property
    def majority_class(self) -> str:
        """Get the majority class."""
        if not self._is_fitted:
            raise ValueError("Model must be fitted first")
        if self._majority_class is None:
            raise ValueError("Model not fitted properly")
        return self._majority_class
