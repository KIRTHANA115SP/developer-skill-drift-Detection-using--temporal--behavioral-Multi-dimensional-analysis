# DevDrift
### Developer Skill Drift Detection Using Multi-Dimensional Temporal Behavioral Analysis

**DevDrift** is a developer-analytics platform designed to identify changes in developer-related behavioural patterns over time. It analyses repository activity, compares category-specific signals against historical baselines, detects potential negative drift, classifies behavioural trajectories, and generates predictive insights and targeted learning recommendations.

Rather than treating developer activity as a single score, DevDrift examines five dimensions independently:

- Security
- Testing
- Documentation
- Concurrency
- Performance

> **Important:** DevDrift analyses observable repository activity as a proxy for developer-related behaviours. Its outputs are analytical indicators, not definitive measurements of individual competence or performance.

---

## 1. Problem Statement

Traditional developer analytics often focus on static metrics, code quality snapshots, or aggregate productivity indicators. These approaches may overlook gradual changes in specific engineering practices over time.

For example, a developer may maintain consistent overall activity while their testing or documentation practices gradually decline.

DevDrift addresses this challenge by introducing a multi-dimensional temporal analysis approach. It establishes individual historical baselines, monitors changes across behavioural categories, identifies potential negative deviations, and provides recommendations based on detected patterns.

## 2. Key Features

| Feature | Description |
|---|---|
| Multi-dimensional analysis | Independently monitors five engineering-related behavioural categories |
| Temporal feature engineering | Converts repository activity into category-specific time-series signals |
| Personal baseline modelling | Compares recent observations against historical behaviour |
| Drift detection | Identifies negative deviations using configurable sensitivity |
| MSDI-related scoring | Computes category-level drift indicators |
| Trajectory classification | Classifies patterns such as improving, stable, gradual decline, and rapid decline |
| Predictive analytics | Generates three-period forecasts from historical trends |
| Learning recommendations | Suggests targeted micro-learning activities based on detected patterns |
| Scenario Lab | Demonstrates improving, declining, stable, mixed, and sudden-change scenarios |
| GitHub integration | Supports repository-based analysis using GitHub data |
| Historical analytics | Stores analysis runs and supports historical views |
| Reporting | Supports PDF reports and CSV exports |
| Interactive dashboard | Provides visual summaries, alerts, trends, and recommendations |

## 3. System Architecture

DevDrift follows a modular, layered architecture.

```text
             DATA SOURCES
                   |
          +--------+--------+
          |                 |
      GitHub API        Scenario Lab
          |                 |
          +--------+--------+
                   |
          DATA COLLECTION
                   |
          FEATURE ENGINEERING
                   |
       MULTI-DIMENSIONAL SIGNALS
                   |
          TEMPORAL ANALYSIS
                   |
       +-----------+-----------+
       |           |           |
   Baseline     Drift       CUSUM-style
   Comparison   Scoring     Evidence
       |           |           |
       +-----------+-----------+
                   |
       TRAJECTORY CLASSIFICATION
                   |
          PREDICTIVE ANALYTICS
                   |
       RECOMMENDATION ENGINE
                   |
          FASTAPI BACKEND
                   |
       +-----------+-----------+
       |                       |
   React Dashboard         SQLite
       |                  Persistence
       |
  Visualizations, Alerts,
  Reports and Insights
```

### Technology Layers

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React, Vite, JavaScript | Interactive dashboard and visual analytics |
| Backend | Python, FastAPI | API endpoints and request orchestration |
| Analytics | Python | Feature extraction, drift scoring, trajectory analysis, and forecasting |
| Integration | GitHub REST API | Repository activity collection |
| Persistence | SQLite | Historical analysis records |
| Reporting | Python PDF generation | Exportable analysis reports |

## 4. Behavioural Dimensions

DevDrift evaluates five categories independently.

| Dimension | Focus |
|---|---|
| Security | Security-related engineering practices |
| Testing | Testing and validation activities |
| Documentation | Documentation and maintenance practices |
| Concurrency | Synchronization and concurrency-related practices |
| Performance | Performance optimization and benchmarking practices |

The resulting signals are intended to represent observable behavioural patterns associated with these dimensions. They should be interpreted in the context of repository size, task type, team practices, and available data.

## 5. Analytical Workflow

1. **Data collection:** Retrieve accessible repository activity or use controlled synthetic scenarios.
2. **Feature engineering:** Transform collected activity into numerical signals across the five dimensions.
3. **Baseline comparison:** Establish a historical reference for each category.
4. **Drift analysis:** Calculate negative deviations and category-level drift indicators.
5. **Change evidence:** Evaluate CUSUM-style evidence and configured alert conditions.
6. **Trajectory classification:** Identify the direction and rate of behavioural change.
7. **Predictive analytics:** Estimate future trends using linear regression.
8. **Recommendation generation:** Produce category-specific learning suggestions.
9. **Visualization and persistence:** Present results through the dashboard and retain supported analysis history.

## 6. Technology Stack

- **Frontend:** React, Vite, JavaScript, CSS
- **Backend:** Python, FastAPI
- **Data processing:** Python analytical modules
- **Data integration:** GitHub REST API
- **Database:** SQLite
- **Version control:** Git and GitHub

## 7. Project Structure

```text
developer-skill-drift/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── demo.py
│   │   ├── drift.py
│   │   ├── features.py
│   │   ├── forecast.py
│   │   ├── github_client.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── report.py
│   │   └── storage.py
│   │
│   ├── tests/
│   ├── data/
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   └── package-lock.json
│
├── .gitignore
└── README.md
```

## 8. Installation and Setup

### Prerequisites

- Python installed
- Node.js and npm installed
- Git installed
- GitHub account (for repository-based analysis)

### Step 1: Clone the repository

```bash
git clone https://github.com/KIRTHANA115SP/developer-skill-drift-Detection-using--temporal--behavioral-Multi-dimensional-analysis.git

cd developer-skill-drift-Detection-using--temporal--behavioral-Multi-dimensional-analysis
```

### Step 2: Configure the backend

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Configure your GitHub token in `backend/.env` if using authenticated GitHub analysis:

```env
GITHUB_TOKEN=your_github_token_here
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

### Step 3: Configure the frontend

Open a second terminal and navigate to the project root:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the frontend environment file:

```powershell
Copy-Item .env.example .env
```

The example configuration uses:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open the local URL displayed by Vite in your browser.

**Note:** Run the backend and frontend in separate terminals. If your application configuration uses different startup commands or environment variables, follow the corresponding project files.

## 9. Operating Modes

### Scenario Lab

Scenario Lab provides controlled synthetic scenarios for exploring the analytical workflow without requiring external repository access.

Available scenarios include:

- Mixed showcase
- Improving
- Declining
- Stable
- Sudden change

These scenarios help demonstrate how the system responds to different temporal patterns.

### GitHub Mode

GitHub mode supports repository-based analysis using accessible GitHub activity and the configured authentication token.

The availability and completeness of repository information influence the resulting analysis.

## 10. Testing and Evaluation

The project includes automated backend tests covering:

- Sparse-data handling and evaluation behaviour
- Analysis history storage
- Historical record retrieval

Synthetic scenarios are also used to inspect the behaviour of the analytical pipeline under controlled conditions.

Synthetic scenario results demonstrate functional behaviour; they do not establish real-world predictive validity or prove that repository signals accurately measure developer competence.

## 11. Limitations and Future Scope

### Current Limitations

- Repository activity is an incomplete proxy for actual engineering skills.
- Sparse or inconsistent repository data can affect signal quality.
- Synthetic scenarios cannot substitute for validation using real-world labelled observations.
- Forecasts based on linear regression may not capture complex behavioural changes.
- Alert thresholds and analytical parameters require further calibration.
- The current prototype is intended for local development and academic demonstration.

### Future Enhancements

- Validation using larger real-world repository datasets.
- Comparative evaluation of alternative temporal drift-detection algorithms.
- Improved adaptive threshold calibration.
- More robust forecasting models.
- Expanded recommendation intelligence.
- Team-level behavioural analytics.
- Stronger authentication, access control, and deployment security.
- Evaluation using suitable labelled outcomes and forecasting error metrics.

## 12. Author

**Kirthana SP**  
Integrated M.Tech. Software Engineering  
Vellore Institute of Technology (VIT), Vellore, India

---

### Project

**DevDrift — Developer Skill Drift Detection Using Multi-Dimensional Temporal Behavioral Analysis**

*Turning repository activity into temporal insights for continuous engineering improvement.*