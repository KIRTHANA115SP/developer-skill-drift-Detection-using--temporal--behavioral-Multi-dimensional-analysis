import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "devdrift.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mode TEXT NOT NULL,
            repository TEXT NOT NULL,
            developer TEXT NOT NULL,
            events INTEGER NOT NULL,
            alerts INTEGER NOT NULL,
            average_drift REAL NOT NULL,
            average_signal REAL NOT NULL,
            results_json TEXT NOT NULL,
            payload_json TEXT
        )""")
        # Safe migration for databases created by earlier DevDrift versions.
        columns = {row[1] for row in c.execute("PRAGMA table_info(runs)").fetchall()}
        if "payload_json" not in columns:
            c.execute("ALTER TABLE runs ADD COLUMN payload_json TEXT")
        c.commit()


def save_run(payload):
    results = payload.get("results", [])
    ts = datetime.now(timezone.utc).isoformat()
    alerts = sum(1 for r in results if r.get("alert"))
    avg_drift = sum(float(r.get("drift_score", 0)) for r in results) / len(results) if results else 0
    avg_signal = sum(float(r.get("current_score", 0)) for r in results) / len(results) if results else 0
    with _conn() as c:
        cur = c.execute("INSERT INTO runs(timestamp,mode,repository,developer,events,alerts,average_drift,average_signal,results_json,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (ts,payload.get("mode",""),payload.get("repository",""),payload.get("developer",""),payload.get("events_collected",0),alerts,avg_drift,avg_signal,json.dumps(results),json.dumps(payload)))
        c.commit()
        return cur.lastrowid, ts


def overview(limit=12):
    with _conn() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    total_runs = len(rows)
    devs = {r["developer"] for r in rows}
    repos = {r["repository"] for r in rows}
    total_events = sum(r["events"] for r in rows)
    total_alerts = sum(r["alerts"] for r in rows)
    avg_drift = sum(r["average_drift"] for r in rows) / total_runs if rows else 0
    cat = {}
    recent_alerts = []
    for row in rows:
        for r in json.loads(row["results_json"]):
            name = r["category"]
            d = cat.setdefault(name, {"category": name, "runs": 0, "alerts": 0, "average_drift": 0.0})
            d["runs"] += 1; d["alerts"] += int(bool(r.get("alert"))); d["average_drift"] += float(r.get("drift_score",0))
            if r.get("alert"):
                recent_alerts.append({"timestamp": row["timestamp"], "developer": row["developer"], "repository": row["repository"], "category": name, "drift_score": r.get("drift_score",0), "trajectory": r.get("trajectory","stable")})
    category_alerts = []
    for d in cat.values():
        d["average_drift"] = round(d["average_drift"] / d["runs"], 2)
        d["alert_rate"] = round(d["alerts"] / d["runs"] * 100, 1)
        category_alerts.append(d)
    trend = [{"run": r["id"], "timestamp": r["timestamp"], "developer": r["developer"], "average_drift": round(r["average_drift"],2), "average_signal": round(r["average_signal"],2), "alerts": r["alerts"]} for r in reversed(rows[-limit:])]
    recent_runs = [{"id": r["id"], "timestamp": r["timestamp"], "developer": r["developer"], "repository": r["repository"], "events": r["events"], "alerts": r["alerts"], "average_drift": round(r["average_drift"],2), "average_signal": round(r["average_signal"],2)} for r in rows[:limit]]
    return {"total_runs": total_runs, "unique_developers": len(devs), "unique_repositories": len(repos), "total_events": total_events, "alert_rate": round(total_alerts / total_runs * 100,1) if total_runs else 0, "average_drift": round(avg_drift,2), "category_alerts": sorted(category_alerts,key=lambda x:x["alert_rate"],reverse=True), "drift_trend": trend, "recent_alerts": recent_alerts[:10], "recent_runs": recent_runs}


def run_history(limit=50):
    """Return saved analysis snapshots, newest first, for restoration and audit."""
    limit = max(1, min(int(limit or 50), 200))
    with _conn() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    output = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if not payload:
            # Backward-compatible history row from a pre-snapshot database.
            payload = {"results": json.loads(row["results_json"]), "mode": row["mode"],
                       "repository": row["repository"], "developer": row["developer"],
                       "events_collected": row["events"], "collection": {}, "categories": [],
                       "params": {}, "sufficient_history": False}
        payload["run_id"] = row["id"]
        payload["timestamp"] = row["timestamp"]
        payload["history_summary"] = {"id": row["id"], "timestamp": row["timestamp"],
            "mode": row["mode"], "repository": row["repository"], "developer": row["developer"],
            "events": row["events"], "alerts": row["alerts"],
            "average_drift": round(row["average_drift"], 2),
            "average_signal": round(row["average_signal"], 2)}
        output.append(payload)
    return output


def alert_history(limit=100):
    """Return recent alerts with stable IDs so the UI can acknowledge them."""
    runs = run_history(min(max(int(limit or 100), 1), 200))
    alerts = []
    for run in runs:
        for item in run.get("results", []):
            if item.get("alert"):
                alerts.append({
                    "id": f"{run.get('run_id')}:{item.get('category', 'unknown')}",
                    "run_id": run.get("run_id"), "timestamp": run.get("timestamp"),
                    "mode": run.get("mode"), "repository": run.get("repository"),
                    "developer": run.get("developer"), "category": item.get("category"),
                    "drift_score": item.get("drift_score", 0), "trajectory": item.get("trajectory", "stable"),
                    "current_score": item.get("current_score", 0), "baseline_mean": item.get("baseline_mean", 0),
                    "recommendation": item.get("recommendation", "Review the observed category-level signal."),
                    "explanation": item.get("explanation", []), "result": item,
                })
    return alerts[:limit]
