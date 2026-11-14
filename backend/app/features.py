from collections import defaultdict
from datetime import datetime
import math
import pandas as pd

CATEGORIES = ["Security", "Testing", "Concurrency", "Documentation", "Performance"]

# These are observable behavioral proxies, not direct measurements of human skill.
# The feature definitions are deliberately transparent so every score can be explained.
FEATURES = {
    "Security": [
        ("security_activity", 0.35),
        ("secure_practice_signals", 0.30),
        ("security_review_risk", 0.20),
        ("security_issue_signals", 0.15),
    ],
    "Testing": [
        ("test_activity", 0.35),
        ("test_practice_signals", 0.30),
        ("test_review_corrections", 0.20),
        ("test_code_ratio_proxy", 0.15),
    ],
    "Concurrency": [
        ("concurrency_activity", 0.35),
        ("safe_concurrency_signals", 0.30),
        ("concurrency_review_risk", 0.20),
        ("concurrency_issue_signals", 0.15),
    ],
    "Documentation": [
        ("documentation_activity", 0.40),
        ("documentation_practice_signals", 0.30),
        ("documentation_review_risk", 0.15),
        ("documentation_consistency", 0.15),
    ],
    "Performance": [
        ("performance_activity", 0.35),
        ("optimization_signals", 0.30),
        ("performance_review_risk", 0.20),
        ("performance_issue_signals", 0.15),
    ],
}

KEYWORDS = {
    "Security": ["auth", "security", "token", "password", "permission", "sanitize", "validation", "vulnerability", "xss", "csrf", "encrypt"],
    "Testing": ["test", "pytest", "junit", "coverage", "mock", "assert", "spec", "regression"],
    "Concurrency": ["thread", "async", "await", "lock", "mutex", "race", "parallel", "concurrent", "synchron", "queue"],
    "Documentation": ["docs", "documentation", "readme", "comment", "guide", "api doc", "changelog"],
    "Performance": ["performance", "optimi", "cache", "latency", "throughput", "benchmark", "memory", "profil"],
}

POSITIVE = {
    "Security": ["secure", "harden", "sanitize", "validate", "encrypt", "auth"],
    "Testing": ["test", "coverage", "assert", "mock", "regression", "pytest", "junit"],
    "Concurrency": ["thread-safe", "synchron", "async", "await", "lock", "mutex"],
    "Documentation": ["documentation", "readme", "docs", "guide", "changelog"],
    "Performance": ["optimi", "cache", "benchmark", "profil", "latency", "throughput"],
}

NEGATIVE = {
    "Security": ["vulnerability", "exploit", "insecure", "security bug", "missing validation"],
    "Testing": ["missing test", "failing test", "test failure", "without test", "no test", "coverage drop"],
    "Concurrency": ["race condition", "deadlock", "thread safety bug", "concurrency bug"],
    "Documentation": ["missing docs", "outdated docs", "documentation issue"],
    "Performance": ["slow", "latency issue", "performance bug", "memory leak", "bottleneck"],
}


def _hits(text: str, words: list[str]) -> int:
    text = (text or "").lower()
    return sum(1 for w in words if w in text)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _feature_vector(event: dict, category: str) -> tuple[float, dict, dict]:
    """Return score, feature vector, and evidence for one observable event.

    Real GitHub events can provide richer numeric fields (files changed,
    additions/deletions, review counts, labels). The feature extractor uses
    those fields when available and falls back to transparent text/type
    proxies. It never treats a feature vector as a direct measurement of skill.
    """
    # Synthetic demo events explicitly carry a category signal. To keep the
    # demo explainable, derive illustrative components around that signal.
    if event.get("signals") and category in event["signals"]:
        raw = _clamp(event["signals"][category])
        # These are explicitly illustrative components, not observed data.
        components = {
            FEATURES[category][0][0]: _clamp(raw * 0.90 + 5),
            FEATURES[category][1][0]: _clamp(raw * 1.05 - 2),
            FEATURES[category][2][0]: _clamp(raw * 0.95 + 3),
            FEATURES[category][3][0]: _clamp(raw * 1.02 - 1),
        }
        evidence = {
            "relevant_events": 1,
            "positive_hits": 1 if raw >= 60 else 0,
            "negative_hits": 1 if raw < 45 else 0,
            "keyword_hits": 1,
            "event_types": {event.get("type", "unknown"): 1},
            "proxy": "illustrative demo signal",
        }
        return raw, components, evidence

    text = event.get("message", "") or ""
    text_lower = text.lower()
    keyword_hits = _hits(text, KEYWORDS[category])
    positive_hits = _hits(text, POSITIVE[category])
    negative_hits = _hits(text, NEGATIVE[category])
    event_type = event.get("type", "")

    # Numeric evidence from richer GitHub collection, if present.
    files_changed = float(event.get("files_changed", 0) or 0)
    additions = float(event.get("additions", 0) or 0)
    deletions = float(event.get("deletions", 0) or 0)
    review_count = float(event.get("review_count", 0) or 0)
    correction_count = float(event.get("correction_count", 0) or 0)
    issue_count = float(event.get("issue_count", 0) or 0)
    test_files = float(event.get("test_files_changed", 0) or 0)
    category_file_fields = {
        "Security": "security_files_changed",
        "Testing": "test_files_changed",
        "Concurrency": "concurrency_files_changed",
        "Documentation": "documentation_files_changed",
        "Performance": "performance_files_changed",
    }
    category_files = float(event.get(category_file_fields[category], 0) or 0)

    relevant = keyword_hits > 0 or category_files > 0 or review_count > 0 or correction_count > 0 or issue_count > 0
    if not relevant:
        # Neutral score: absence of evidence is not treated as poor skill.
        neutral = {name: 50.0 for name, _ in FEATURES[category]}
        return 50.0, neutral, {
            "relevant_events": 0,
            "positive_hits": 0,
            "negative_hits": 0,
            "keyword_hits": 0,
            "event_types": {event_type: 1},
            "proxy": "no category-specific observable evidence",
        }

    # Shared normalized signals.
    activity = _clamp(35 + 12 * math.log1p(category_files + keyword_hits))
    practice = _clamp(50 + 18 * positive_hits - 18 * negative_hits)
    review_risk = _clamp(70 + 3 * min(review_count, 5) - 12 * correction_count - 6 * negative_hits + 4 * positive_hits)
    issue_signal = _clamp(65 - 10 * issue_count - 8 * negative_hits + 5 * positive_hits)

    if category == "Testing":
        test_ratio = _clamp(50 + 20 * math.log1p(test_files) - 4 * math.log1p(max(additions - deletions, 0)))
        components = {
            "test_activity": activity,
            "test_practice_signals": practice,
            "test_review_corrections": review_risk,
            "test_code_ratio_proxy": test_ratio,
        }
    elif category == "Documentation":
        consistency = _clamp(50 + 10 * keyword_hits - 10 * negative_hits)
        components = {
            "documentation_activity": activity,
            "documentation_practice_signals": practice,
            "documentation_review_risk": review_risk,
            "documentation_consistency": consistency,
        }
    elif category == "Security":
        components = {
            "security_activity": activity,
            "secure_practice_signals": practice,
            "security_review_risk": review_risk,
            "security_issue_signals": issue_signal,
        }
    elif category == "Concurrency":
        components = {
            "concurrency_activity": activity,
            "safe_concurrency_signals": practice,
            "concurrency_review_risk": review_risk,
            "concurrency_issue_signals": issue_signal,
        }
    else:
        components = {
            "performance_activity": activity,
            "optimization_signals": practice,
            "performance_review_risk": review_risk,
            "performance_issue_signals": issue_signal,
        }

    weights = dict(FEATURES[category])
    score = sum(components[name] * weights[name] for name in components)
    return _clamp(score), components, {
        "relevant_events": 1,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
        "keyword_hits": keyword_hits,
        "event_types": {event_type: 1},
        "proxy": "GitHub observable feature heuristic",
    }


def build_temporal_features(events, weeks=8):
    if not events:
        return {c: [] for c in CATEGORIES}

    rows = []
    for e in events:
        try:
            dt = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        except Exception:
            continue
        row = dict(e)
        row["date"] = dt
        rows.append(row)

    if not rows:
        return {c: [] for c in CATEGORIES}

    df = pd.DataFrame(rows).sort_values("date")
    end = df["date"].max()
    start = end - pd.Timedelta(weeks=weeks)
    df = df[df["date"] >= start].copy()
    df["week"] = df["date"].dt.to_period("W").astype(str)
    weeks_sorted = sorted(df["week"].unique())

    out = {c: [] for c in CATEGORIES}
    grouped = df.groupby("week")

    for wk in weeks_sorted:
        g = grouped.get_group(wk)
        for category in CATEGORIES:
            scores = []
            feature_sums = defaultdict(float)
            feature_counts = defaultdict(int)
            relevant = positive = negative = keyword = 0
            event_types = defaultdict(int)

            for _, row in g.iterrows():
                score, components, evidence = _feature_vector(row.to_dict(), category)
                if evidence["relevant_events"]:
                    scores.append(score)
                    relevant += evidence["relevant_events"]
                    positive += evidence["positive_hits"]
                    negative += evidence["negative_hits"]
                    keyword += evidence["keyword_hits"]
                    for event_type, count in evidence.get("event_types", {}).items():
                        event_types[event_type] += count
                    for name, value in components.items():
                        feature_sums[name] += value
                        feature_counts[name] += 1

            score = round(sum(scores) / len(scores), 2) if scores else 50.0
            feature_breakdown = []
            for name, weight in FEATURES[category]:
                value = round(feature_sums[name] / feature_counts[name], 2) if feature_counts[name] else 50.0
                feature_breakdown.append({
                    "name": name,
                    "value": value,
                    "weight": weight,
                    "contribution": round(value * weight, 2),
                })

            out[category].append({
                "week": wk,
                "score": score,
                "evidence": {
                    "relevant_events": relevant,
                    "positive_hits": positive,
                    "negative_hits": negative,
                    "keyword_hits": keyword,
                    "event_types": dict(event_types),
                },
                "features": feature_breakdown,
            })

    return out
