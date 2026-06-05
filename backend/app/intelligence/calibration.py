"""Signal calibration helpers for self-learning workflows.

The app should learn only from labeled outcomes that pass an evaluation gate.
This module keeps calibration math outside Flask so it can be tested and reused
by future model feedback jobs.
"""

from __future__ import annotations

from typing import Any

import numpy as np


CALIBRATION_GATE = 50


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _outcome_to_label(outcome: Any) -> float:
    return 1.0 if str(outcome or "").upper() == "WIN" else 0.0


def build_not_ready_response(sample_size: int, gate: int = CALIBRATION_GATE) -> dict[str, Any]:
    needed = max(gate - sample_size, 0)
    return {
        "ready": False,
        "sample_size": sample_size,
        "message": (
            f"Need {needed} more labeled trades for calibration. "
            f"Click 'Sync Labels' to populate from your trade history."
        ),
        "curve": [],
        "ece": None,
    }


def build_calibrated_lookup(ir: Any) -> list[dict[str, float | int]]:
    lookup: list[dict[str, float | int]] = []
    for raw in range(5, 101, 5):
        predicted = float(ir.transform([float(raw)])[0])
        lookup.append({"raw": raw, "calibrated": round(predicted * 100, 1)})
    return lookup


def fit_isotonic_calibration(labels: list[Any], gate: int = CALIBRATION_GATE) -> dict[str, Any]:
    sample_size = len(labels)
    if sample_size < gate:
        return build_not_ready_response(sample_size, gate=gate)

    x_raw = np.array([float(_get(label, "confidence_raw") or 0.0) for label in labels], dtype=float)
    y = np.array([_outcome_to_label(_get(label, "outcome")) for label in labels], dtype=float)

    import sklearn.isotonic as _iso

    ir = _iso.IsotonicRegression(out_of_bounds="clip", increasing="auto")
    y_pred = ir.fit_transform(x_raw, y)

    curve, bin_empirical, bin_predicted, bin_counts = _build_curve(x_raw, y, y_pred)
    total = sum(bin_counts)
    ece = (
        sum((abs(empirical - predicted) * count) for empirical, predicted, count in zip(bin_empirical, bin_predicted, bin_counts))
        / total
        if total > 0
        else 0
    )

    return {
        "ready": True,
        "sample_size": sample_size,
        "message": None,
        "curve": curve,
        "ece": round(ece, 4),
        "overall_wr": round(float(y.mean() * 100), 1),
        "wins": int(y.sum()),
        "losses": sample_size - int(y.sum()),
        "calibrated_fn": build_calibrated_lookup(ir),
    }


def _build_curve(x_raw: np.ndarray, y: np.ndarray, y_pred: np.ndarray) -> tuple[list[dict[str, float | int]], list[float], list[float], list[int]]:
    n_bins = 10
    bins = np.linspace(x_raw.min(), x_raw.max(), n_bins + 1)
    curve: list[dict[str, float | int]] = []
    bin_empirical: list[float] = []
    bin_predicted: list[float] = []
    bin_counts: list[int] = []

    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        if i == n_bins - 1:
            mask = (x_raw >= lo) & (x_raw <= hi)
        else:
            mask = (x_raw >= lo) & (x_raw < hi)
        count = int(mask.sum())
        if count > 0:
            emp_wr = float(y[mask].mean() * 100)
            pred_wr = float(y_pred[mask].mean() * 100)
        else:
            emp_wr = 0.0
            pred_wr = 0.0
        curve.append({
            "bin_low": round(float(lo), 1),
            "bin_high": round(float(hi), 1),
            "empirical": round(emp_wr, 1),
            "calibrated": round(pred_wr, 1),
            "count": count,
        })
        if count > 0:
            bin_empirical.append(emp_wr / 100)
            bin_predicted.append(pred_wr / 100)
            bin_counts.append(count)

    return curve, bin_empirical, bin_predicted, bin_counts
