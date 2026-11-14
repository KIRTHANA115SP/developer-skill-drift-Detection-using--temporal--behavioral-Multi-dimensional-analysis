from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class AnalyzeParams(BaseModel):
    sensitivity: float = Field(default=1.0, ge=0.25, le=3.0)
    hazard_rate: float = Field(default=0.15, ge=0.01, le=0.95)
    cusum_k: float = Field(default=0.25, ge=0.0, le=2.0)
    cusum_h: float = Field(default=4.0, ge=0.5, le=20.0)

class AnalyzeRequest(BaseModel):
    owner: str = "demo"
    repo: str = "demo"
    username: Optional[str] = None
    weeks: int = Field(default=8, ge=4, le=52)
    demo: bool = True
    scenario: str = "mixed"
    params: AnalyzeParams = Field(default_factory=AnalyzeParams)

class Evidence(BaseModel):
    relevant_events: int = 0
    positive_hits: int = 0
    negative_hits: int = 0
    keyword_hits: int = 0
    event_types: Dict[str, int] = Field(default_factory=dict)

class FeatureContribution(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float

class ForecastPoint(BaseModel):
    period: str
    predicted: float
    lower: float
    upper: float

class Forecast(BaseModel):
    horizon: int = 3
    confidence: float = 0.8
    points: List[ForecastPoint] = Field(default_factory=list)
    trend: str = "stable"

class CategoryPoint(BaseModel):
    week: str
    score: float
    evidence: Evidence = Field(default_factory=Evidence)
    features: List[FeatureContribution] = Field(default_factory=list)

class CategoryEvidence(BaseModel):
    current: Evidence
    historical_average_relevant_events: float
    proxy_definition: str
    feature_breakdown: List[FeatureContribution] = Field(default_factory=list)

class CategoryResult(BaseModel):
    category: str
    current_score: float
    baseline_mean: float
    baseline_std: float
    adaptive_threshold: float
    deviation: float
    drift_score: float
    trajectory: str
    direction: str
    slope: float
    alert: bool
    explanation: List[str]
    evidence: CategoryEvidence
    recommendation: str
    series: List[CategoryPoint]
    forecast: Forecast

class CollectionSummary(BaseModel):
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    review_corrections: int = 0

class AnalysisResponse(BaseModel):
    run_id: int
    timestamp: str
    mode: str
    repository: str
    developer: str
    events_collected: int
    collection: CollectionSummary = Field(default_factory=CollectionSummary)
    categories: List[str]
    results: List[CategoryResult]
    params: AnalyzeParams = Field(default_factory=AnalyzeParams)
    sufficient_history: bool = True
    insufficient_reason: Optional[str] = None
    scenario: Optional[str] = None
    coverage: Dict = Field(default_factory=dict)

class OverviewResponse(BaseModel):
    total_runs: int
    unique_developers: int
    unique_repositories: int
    total_events: int
    alert_rate: float
    average_drift: float
    category_alerts: List[Dict]
    drift_trend: List[Dict]
    recent_alerts: List[Dict]
    recent_runs: List[Dict]
