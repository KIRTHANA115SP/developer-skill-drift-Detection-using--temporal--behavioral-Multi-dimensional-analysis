from datetime import datetime, timedelta, timezone

CATEGORIES = ["Security", "Testing", "Concurrency", "Documentation", "Performance"]


def demo_events(weeks=8, scenario="mixed"):
    """Illustrative events with explicit proxy signals for the demo.

    These values are intentionally synthetic so the dashboard can demonstrate
    the temporal pipeline. They must not be presented as real experiment data.
    """
    end = datetime.now(timezone.utc)
    testing = [82, 80, 78, 76, 72, 66, 60, 52]
    security = [35, 40, 44, 50, 58, 62, 68, 75]
    docs = [45, 46, 44, 47, 46, 45, 47, 46]
    concurrency = [58, 60, 59, 61, 60, 59, 60, 61]
    performance = [62, 64, 63, 65, 66, 67, 68, 69]

    series = {
        "Testing": testing,
        "Security": security,
        "Documentation": docs,
        "Concurrency": concurrency,
        "Performance": performance,
    }
    # Scenario Lab provides labelled, reproducible patterns. All values are synthetic.
    stable = [50, 51, 49, 50, 50, 49, 51, 50]
    target = {
        "improving": ("Security", [30, 35, 40, 48, 55, 63, 70, 78]),
        "declining": ("Testing", [88, 85, 81, 75, 67, 59, 50, 42]),
        "stable": ("Documentation", stable),
        "sudden_change": ("Performance", [74, 75, 73, 74, 75, 72, 48, 40]),
    }
    if scenario in target:
        category, values = target[scenario]
        series = {name: list(stable) for name in CATEGORIES}
        series[category] = values
    else:
        scenario = "mixed"

    events = []
    for i in range(weeks):
        day = end - timedelta(weeks=weeks - i)
        for category, values in series.items():
            # 2 illustrative events per category per week gives us enough
            # evidence for the explanation panel.
            for j in range(2):
                events.append({
                    "type": "commit" if j == 0 else "pull_request",
                    "date": (day + timedelta(days=j)).isoformat(),
                    "message": f"{category.lower()} development activity",
                    "author": "demo-user",
                    "signals": {category: values[min(len(values)-1, int(i * len(values) / max(weeks, 1)))]},
                })

    return events
