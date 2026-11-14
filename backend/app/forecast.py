import numpy as np
from sklearn.linear_model import LinearRegression


def forecast_series(values, horizon=3, confidence=0.80):
    values = [float(v) for v in values]
    if len(values) < 4:
        return {"horizon": horizon, "confidence": confidence, "points": [], "trend": "insufficient-data"}
    x = np.arange(len(values), dtype=float).reshape(-1, 1)
    y = np.asarray(values, dtype=float)
    model = LinearRegression().fit(x, y)
    slope = float(model.coef_[0])
    pred_hist = model.predict(x)
    residual = y - pred_hist
    se = float(np.std(residual, ddof=1)) if len(values) > 2 else 5.0
    z = 1.2816 if confidence <= 0.80 else 1.6449
    points = []
    for step in range(1, horizon + 1):
        idx = len(values) - 1 + step
        pred = float(np.clip(model.predict(np.array([[idx]]))[0], 0, 100))
        band = max(2.0, z * se * np.sqrt(1 + 1 / len(values) + (idx - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2)))
        points.append({"period": f"F+{step}", "predicted": round(pred, 2), "lower": round(max(0, pred-band), 2), "upper": round(min(100, pred+band), 2)})
    trend = "rapid-decline" if slope <= -8 else "gradual-decline" if slope <= -2 else "improving" if slope >= 2 else "stable"
    return {"horizon": horizon, "confidence": confidence, "points": points, "trend": trend}
