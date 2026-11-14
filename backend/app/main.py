import os
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv
from .models import AnalyzeRequest, AnalyzeParams, AnalysisResponse, OverviewResponse
from .github_client import GitHubClient
from .features import build_temporal_features, CATEGORIES
from .drift import analyze_category, classify_trajectory
from .demo import demo_events
from .storage import init_db, save_run, overview, run_history, alert_history
from .report import build_report

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
app = FastAPI(title="Developer Skill Drift Detection API", version="0.8.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
init_db()


def github_error_detail(error: requests.HTTPError) -> tuple[int, str]:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", 502)
    headers = getattr(response, "headers", {}) or {}
    if status == 401:
        return 400, "GitHub rejected the credential. Check GITHUB_TOKEN, then restart the backend. Public repositories may be queried without a token."
    if status == 403 and headers.get("X-RateLimit-Remaining") == "0":
        return 429, "GitHub API rate limit reached. Wait for the reset or configure GITHUB_TOKEN in backend/.env."
    if status == 404:
        return 404, "Repository or activity was not found or is not visible to this GitHub account. Verify owner, repository, username, and token permissions."
    if status == 403:
        return 403, "GitHub denied access. Check repository permissions and token scopes; secondary API rate limits may also apply."
    if status >= 500:
        return 502, "GitHub is temporarily unavailable. Retry in a little while."
    return 400, f"GitHub rejected the request (HTTP {status}). Check repository details and permissions."

@app.get("/api/health")
def health():
    return {"status":"ok", "github_token_configured":bool(os.getenv("GITHUB_TOKEN"))}

@app.get("/api/github/contributors")
def github_contributors(owner: str, repo: str, limit: int = 20):
    """List contributors for a repository to help users select multiple profiles."""
    try:
        client = GitHubClient()
        return {"contributors": client.contributors(owner, repo, limit)}
    except requests.HTTPError as e:
        status, detail = github_error_detail(e)
        raise HTTPException(status_code=status, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/overview", response_model=OverviewResponse)
def get_overview():
    return overview()

@app.get("/api/history")
def get_history(limit: int = 50):
    """Saved analysis snapshots; selecting one in the UI restores that exact result."""
    return {"runs": run_history(limit)}

@app.get("/api/alerts")
def get_alert_history(limit: int = 100):
    """Recent drift alerts across saved runs (not only the latest dashboard view)."""
    return {"alerts": alert_history(limit)}

@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze(req: AnalyzeRequest):
    if req.demo:
        events = demo_events(req.weeks, req.scenario); mode = "scenario_lab"; developer = req.username or f"scenario-{req.scenario}"
    else:
        try:
            client = GitHubClient()
            if not req.owner or not req.repo: raise HTTPException(status_code=400, detail="Enter both repository owner and repository name.")
            if not req.username: raise HTTPException(status_code=400, detail="Enter the GitHub username of the developer you want to analyze.")
            events = client.collect(req.owner, req.repo, req.weeks, req.username); mode="github"; developer=req.username
        except requests.HTTPError as e:
            status, detail = github_error_detail(e)
            raise HTTPException(status_code=status, detail=detail)
        except HTTPException: raise
        except Exception as e: raise HTTPException(status_code=500, detail=str(e))
    features = build_temporal_features(events, req.weeks)
    temporal_points = max((len(features.get(category, [])) for category in CATEGORIES), default=0)
    sufficient_history = (len(events) >= 8 and temporal_points >= 4) if mode == "github" else True
    results = []
    # Hard quality gate: real GitHub results must have enough events and temporal bins.
    # Never emit a drift classification or forecast from a sparse real-world sample.
    if sufficient_history:
        for category in CATEGORIES:
            result = analyze_category(category, features.get(category, []), req.params.model_dump())
            if result: results.append(result)
    collection = {"commits":sum(e.get("type")=="commit" for e in events), "pull_requests":sum(e.get("type")=="pull_request" for e in events), "issues":sum(e.get("type")=="issue" for e in events), "review_corrections":sum(int(e.get("correction_count",0) or 0) for e in events)}
    coverage = {
        "commits": {"count": collection["commits"], "available": collection["commits"] > 0},
        "pull_requests": {"count": collection["pull_requests"], "available": collection["pull_requests"] > 0},
        "issues": {"count": collection["issues"], "available": collection["issues"] > 0},
        "reviews": {"count": collection["review_corrections"], "available": collection["review_corrections"] > 0},
        "temporal_points": temporal_points,
    }
    payload = {"mode":mode,"repository":(f"Scenario Lab / {req.scenario}" if mode == "scenario_lab" else f"{req.owner}/{req.repo}"),"developer":developer,"events_collected":len(events),"collection":collection,"coverage":coverage,"categories":CATEGORIES,"results":results,"params":req.params.model_dump(),"scenario":req.scenario if mode == "scenario_lab" else None,"sufficient_history":sufficient_history,"insufficient_reason": None if sufficient_history else f"Only {len(events)} event(s) across {temporal_points} weekly observation(s). At least 8 events and 4 temporal observations are required for real-data drift inference."}
    run_id, ts = save_run(payload); payload["run_id"]=run_id; payload["timestamp"]=ts
    return payload

@app.post("/api/report")
def report(payload: dict):
    pdf = build_report(payload)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition":"attachment; filename=developer-skill-drift-report.pdf"})


@app.get("/api/evaluation")
def evaluate_scenarios():
    """Evaluate the detector against labelled, deterministic synthetic scenarios.

    Metrics are calculated against scenario labels, not real developer outcomes.
    The returned cases make this limitation explicit for reports and demos.
    """
    from .models import CategoryPoint
    scenarios = {
        "improving": {"category": "Security", "values": [35, 39, 44, 50, 57, 63, 69, 76], "expected_alert": False},
        "declining": {"category": "Testing", "values": [86, 84, 80, 75, 68, 61, 53, 44], "expected_alert": True},
        "stable": {"category": "Documentation", "values": [48, 49, 48, 50, 49, 48, 49, 48], "expected_alert": False},
        "sudden_change": {"category": "Performance", "values": [75, 76, 74, 75, 74, 73, 48, 42], "expected_alert": True},
    }
    cases = []
    for name, spec in scenarios.items():
        points = []
        for i, value in enumerate(spec["values"]):
            points.append({"week": f"W{i+1}", "score": value, "evidence": {"relevant_events": 2, "positive_hits": 1 if value >= 60 else 0, "negative_hits": 1 if value < 45 else 0, "keyword_hits": 2, "event_types": {"commit": 1, "pull_request": 1}}, "features": []})
        result = analyze_category(spec["category"], points, AnalyzeParams().model_dump())
        predicted = bool(result and result.get("alert"))
        expected = bool(spec["expected_alert"])
        cases.append({"scenario": name, "category": spec["category"], "expected_alert": expected, "predicted_alert": predicted, "correct": expected == predicted, "trajectory": result.get("trajectory") if result else "insufficient-data", "msdi": result.get("drift_score") if result else None, "label_source": "predefined synthetic scenario label"})
    tp = sum(c["expected_alert"] and c["predicted_alert"] for c in cases)
    fp = sum((not c["expected_alert"]) and c["predicted_alert"] for c in cases)
    fn = sum(c["expected_alert"] and (not c["predicted_alert"]) for c in cases)
    tn = sum((not c["expected_alert"]) and (not c["predicted_alert"]) for c in cases)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"dataset":"Synthetic scenario benchmark", "warning":"These metrics evaluate four hand-labelled synthetic cases only; they are not estimates of real-world performance.", "cases":cases, "metrics":{"true_positive":tp,"false_positive":fp,"false_negative":fn,"true_negative":tn,"precision":round(precision,3),"recall":round(recall,3),"false_positive_rate":round(fp/(fp+tn),3) if fp+tn else 0.0,"accuracy":round((tp+tn)/len(cases),3) if cases else 0.0}, "sample_size":len(cases)}
