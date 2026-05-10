import pandas as pd

def apply_gs_outlier_filter(series, window=22, threshold=3):
    """
    Based on gs_quant.timeseries.statistics.zscores
    Flags and clamps data spikes that are mathematically impossible.
    """
    # Calculate rolling z-score (The Goldman Way)
    mean = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    
    # Avoid division by zero if std is 0
    std = std.replace(0, 1e-9)
    z_scores = (series - mean) / std

    # "Winsorize" - Clamp values beyond the threshold
    # This prevents 'fake' price wicks from triggering your Buy/Sell signals
    return series.where(z_scores.abs() <= threshold, mean + (z_scores.clip(-threshold, threshold) * std))
