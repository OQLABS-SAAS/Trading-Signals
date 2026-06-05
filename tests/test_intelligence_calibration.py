import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.intelligence.calibration import (  # noqa: E402
    build_not_ready_response,
    fit_isotonic_calibration,
)


def test_build_not_ready_response_tracks_remaining_labels():
    result = build_not_ready_response(17, gate=50)

    assert result["ready"] is False
    assert result["sample_size"] == 17
    assert "Need 33 more labeled trades" in result["message"]
    assert result["curve"] == []
    assert result["ece"] is None


def test_fit_isotonic_calibration_returns_curve_and_lookup():
    labels = []
    for idx in range(60):
        confidence = 45 + idx
        outcome = "WIN" if confidence >= 70 else "LOSS"
        labels.append({"confidence_raw": confidence, "outcome": outcome})

    result = fit_isotonic_calibration(labels, gate=50)

    assert result["ready"] is True
    assert result["sample_size"] == 60
    assert len(result["curve"]) == 10
    assert len(result["calibrated_fn"]) == 20
    assert result["wins"] == 35
    assert result["losses"] == 25
    assert 0 <= result["ece"] <= 1
    assert result["calibrated_fn"][0]["raw"] == 5
    assert result["calibrated_fn"][-1]["raw"] == 100
