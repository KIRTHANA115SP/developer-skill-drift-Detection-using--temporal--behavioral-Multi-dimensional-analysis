import numpy as np
from sklearn.linear_model import LinearRegression
from .forecast import forecast_series

RECOMMENDATIONS = {
    "Security": "Review secure coding, input validation, authentication and common web vulnerabilities.",
    "Testing": "Practice unit testing, assertions, mocking and regression-test design.",
    "Concurrency": "Review synchronization, race conditions, async patterns and thread safety.",
    "Documentation": "Practice API documentation, meaningful comments, README structure and changelogs.",
    "Performance": "Review profiling, caching, algorithmic complexity and performance benchmarking.",
}


def classify_trajectory(values):
    if len(values) < 3:
        return "insufficient-data", "stable", 0.0
    x = np.arange(len(values)).reshape(-1, 1)
    y = np.array(values, dtype=float)
    slope = float(LinearRegression().fit(x, y).coef_[0])
    if slope <= -8:
        return "rapid-decline", "declining", slope
    if slope <= -2:
        return "gradual-decline", "declining", slope
    if slope >= 2:
        return "improving", "improving", slope
    return ("stable-low" if y[-1] < np.mean(y) else "stable"), "stable", slope


def _cusum(values, k=0.25, h=4.0):
    if len(values) < 3:
        return False
    y = np.asarray(values, dtype=float)
    mean = float(np.mean(y[:-1])); scale = max(float(np.std(y[:-1])), 5.0)
    z = (y - mean) / scale
    s = 0.0
    for v in z:
        s = min(0.0, s + v + k)
        if abs(s) >= h:
            return True
    return False


def analyze_category(category, points, params=None):
    params = params or {}
    sensitivity = float(params.get('sensitivity', 1.0))
    hazard = float(params.get('hazard_rate', 0.15))
    cusum_k = float(params.get('cusum_k', 0.25))
    cusum_h = float(params.get('cusum_h', 4.0))
    values = [float(p["score"]) for p in points]
    if len(values) < 4:
        return None
    baseline = np.array(values[:-1], dtype=float)
    current = values[-1]
    mean = float(baseline.mean())
    std = float(baseline.std(ddof=0))
    adaptive_std = max(std, 5.0)
    deviation = (mean - current) / adaptive_std
    drift_score = float(max(0.0, min(100.0, deviation * 25.0 * sensitivity)))
    trajectory, direction, slope = classify_trajectory(values)
    cusum_alert = _cusum(values, cusum_k, cusum_h)
    alert = deviation >= (1.5 / max(sensitivity, 0.25)) and direction == "declining" and (cusum_alert or hazard >= 0.05)
    recent = points[-1].get("evidence", {}) if points else {}
    baseline_evidence = [p.get("evidence", {}) for p in points[:-1]]
    avg_relevant = float(np.mean([e.get("relevant_events", 0) for e in baseline_evidence])) if baseline_evidence else 0.0
    recent_relevant = int(recent.get("relevant_events", 0))
    reasons = []
    if current < mean:
        reasons.append(f"current signal is {abs(mean-current):.1f} points below the personal baseline")
    elif current > mean:
        reasons.append(f"current signal is {abs(current-mean):.1f} points above the personal baseline")
    if slope < 0:
        reasons.append(f"the recent trend is declining ({slope:.1f} points/week)")
    elif slope > 0:
        reasons.append(f"the recent trend is improving ({slope:.1f} points/week)")
    if recent_relevant < avg_relevant and avg_relevant > 0:
        reasons.append("recent category-specific evidence is lower than its historical level")
    if cusum_alert:
        reasons.append("a cumulative change detector found a sustained negative shift")
    if not reasons:
        reasons.append("the current signal remains close to the personal baseline")
    current_features = points[-1].get("features", []) if points else []
    return {
        "category": category, "current_score": round(current,2), "baseline_mean": round(mean,2), "baseline_std": round(std,2),
        "adaptive_threshold": round(adaptive_std,2), "deviation": round(deviation,2), "drift_score": round(drift_score,2),
        "trajectory": trajectory, "direction": direction, "slope": round(slope,2), "alert": alert, "explanation": reasons,
        "evidence": {"current": recent, "historical_average_relevant_events": round(avg_relevant,2), "proxy_definition":"Observable GitHub behavior is used as a behavioral proxy; it is not a direct measurement of human skill.", "feature_breakdown": current_features},
        "recommendation": RECOMMENDATIONS[category] if alert else "Continue monitoring this category against the personal baseline.",
        "series": points, "forecast": forecast_series(values, horizon=3, confidence=0.80),
    }
