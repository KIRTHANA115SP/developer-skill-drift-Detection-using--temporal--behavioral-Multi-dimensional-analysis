# Developer Skill Drift Detection — v0.7

A temporal developer-analytics prototype that converts observable GitHub behavior into category-specific time-series signals, personalized drift detection, predictive forecasting, and adaptive micro-learning recommendations.

## Core capabilities

- GitHub commits / pull requests / issues ingestion
- Five skill-related behavioral dimensions: Security, Testing, Concurrency, Documentation, Performance
- Personalized historical baseline and adaptive drift index (MSDI)
- CUSUM-style sustained-shift evidence with tunable sensitivity parameters
- Trajectory classification: stable-low, stable, improving, gradual-decline, rapid-decline
- 3-period predictive forecast with uncertainty band
- Team-level analytics across saved analysis runs
- PDF report generation
- Algorithm tuning UI
- Dark mode
- Skeleton loading states
- Sparklines in team activity history
- Explainable detection flow from evidence → features → baseline → drift → recommendation
- Explicit insufficient-history warning
- Executive Review Brief with category counts, alert summary, and copyable explanation
- One-click CSV export of category-level analysis results
- Presentation / Review Mode that hides the sidebar and expands the dashboard for project demonstrations
- Multi-profile comparison for 2–5 GitHub contributors in the same repository
- Contributor discovery through the GitHub REST API, with click-to-add profile chips
- Side-by-side category signals, alert counts, and event totals for selected profiles
- Sequential collection to reduce unnecessary API pressure; each profile is saved as a separate analysis run

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Add GITHUB_TOKEN to backend/.env for GitHub mode
uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`
Swagger: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## API

- `GET /api/health`
- `GET /api/github/contributors?owner=OWNER&repo=REPO&limit=20`
- `POST /api/analyze`
- `GET /api/overview`
- `GET /api/history?limit=100`
- `GET /api/alerts?limit=100`
- `POST /api/report`

## GitHub setup

1. For public repositories, a token is optional; anonymous GitHub API access has lower limits. A fine-grained personal access token is recommended for predictable rate limits and is required to access private repositories you are authorized to inspect. Grant only the read access needed for the repositories you intend to analyse.
2. Copy `backend/.env.example` to `backend/.env`.
3. Add `GITHUB_TOKEN=your_token_here` to `backend/.env` when you have a token. Public-repository mode can run without it. Never paste the token into the frontend or commit it to source control.
4. Restart FastAPI, select GitHub mode, enter the repository owner and name, and analyse a username. For multi-profile comparison, use **Load contributors** or enter 2–5 usernames separated by commas.

The collector analyses activity visible through the GitHub REST API. Private repository access depends on the token's repository selection and permissions. GitHub applies rate limits; the app compares profiles sequentially to reduce avoidable request bursts. See the [GitHub REST API rate-limit documentation](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

## Security

Never commit `.env` or a real GitHub token. Use `.env.example` as the template.

## Important interpretation note

The system models **observable repository behavior as skill-related proxy signals**. It does not directly measure a person's human competency. Drift is defined relative to the developer's own historical baseline.

## Multi-profile capstone demo (recommended)

1. Start the backend and frontend using the commands above.
2. Select **GitHub** mode and enter a repository owner and repository name that you are allowed to inspect.
3. Click **Load contributors**. The app queries the repository's visible contributor list. You can also enter usernames manually.
4. Select 2–3 profiles for the first demo (up to five are accepted) and click **Compare profiles**. Each profile is analysed separately against the same repository and time window; results are saved as individual runs.
5. Present the side-by-side category snapshot, then run one profile in the main dashboard and open **Explain detection** for a deeper walkthrough.

### Data and interpretation notes

- Real GitHub analysis requires reachable `api.github.com`. Configure `GITHUB_TOKEN` in `backend/.env` if needed for authenticated access or private repositories.
- Use a least-privilege token with read access only to repositories that you are authorized to analyse. Never expose the token in frontend code or commit it.
- The contributor endpoint reports contributors GitHub exposes for that repository; it does not guarantee that every contributor has enough recent activity for a stable baseline.
- The multi-profile view compares activity-derived proxy signals. It is not a leaderboard and must not be described as a direct ranking of developer skill.
- GitHub REST API requests are rate-limited. Use a small number of profiles during the review, and handle rate-limit or permission errors by checking the repository, token scope, and GitHub API response.

## v0.6 practical workflow additions

- **Action Planner:** converts current category-level analysis into a small prioritized improvement sprint, with completion checkboxes saved in the browser.
- **Experiment Lab:** reruns the same selected data source with an alternate sensitivity value and compares category MSDI/alert changes. This is a sensitivity experiment, not a claim that a threshold is objectively optimal.
- **Data Quality:** surfaces checks for source identification, event volume, temporal coverage, category-series availability, forecast caveats, and proxy limitations.
- **Configurable history window:** choose 4, 8, 12, or 24 weeks for the primary analysis and multi-profile comparisons.
- **Responsible-use language:** emphasizes that low activity is not proof of low skill and the prototype should not be used as the sole basis for employment decisions.

The frontend build could not be verified in this environment because Vite was unavailable after the dependency-install attempt timed out. Run `npm install` in `frontend/` and then `npm run build` locally before presenting. Python backend syntax validation passed.


## v0.6.1 startup fix

- Fixed missing React state initialization for the Action Planner and Experiment Lab that could crash the app during its first render.
- Added a frontend error boundary so future render errors display a readable error message instead of a silent blank page.
- If the app still fails to start, open the browser Console (F12) and check the terminal where `npm run dev` is running. Confirm `npm install` completes successfully.


## v0.7 real-time operations features

- **Live Monitor:** polls the API health endpoint every 10 seconds and shows GitHub token configuration, last analysis, saved snapshots, event count, and historical alert count.
- **Scheduled refresh:** opt-in browser-tab scheduler for periodic re-analysis every 1, 5, or 15 minutes. Keep the browser tab and API running; this is not a server-side daemon. GitHub-mode refreshes consume API quota.
- **Persistent Run History:** full analysis payloads are stored in SQLite; restore an earlier run without re-running collection; filter and export run history to CSV.
- **Historical Alert Inbox:** browse alerts across saved runs, inspect evidence, open the originating run, and acknowledge/reopen alerts. Acknowledgments are stored in the current browser's local storage.
- **API endpoints:** `GET /api/history?limit=100` and `GET /api/alerts?limit=100`. The storage layer migrates older databases by adding a nullable snapshot column; older rows remain visible with limited metadata.
- **Configurable API base URL:** set `VITE_API_URL` in a frontend `.env` file if the backend is hosted somewhere other than `http://127.0.0.1:8000`.

### Live-monitoring behavior

The health indicator checks connectivity every ten seconds. Scheduled analysis is opt-in and runs inside the browser session while the tab is open; it does not continue after the browser closes. Prefer 5 or 15 minute intervals for GitHub mode to avoid unnecessary requests. Synthetic demo mode does not require a GitHub token.


## v0.8 Sparse Data Mode and Evaluation

- The synthetic demonstration mode is now named **Scenario Lab** and includes Mixed showcase, Improving, Declining, Stable, and Sudden change patterns. These are labelled synthetic histories, never real developer data.
- GitHub analyses report per-source coverage and enforce a minimum evidence gate: at least 8 events and 4 temporal observations are required before real-data drift inference is shown. Sparse runs keep the collected counts and explain why classifications/forecasts were suppressed.
- **Algorithm Evaluation** runs a small, deterministic labelled synthetic benchmark and reports precision, recall, false-positive rate, accuracy, and case-level expected/detected alerts. The UI and API explicitly warn that four synthetic cases are not evidence of real-world performance.
- **Data Quality** now shows observed counts for commits, pull requests, issues, and review corrections. Missing sources are described as unavailable evidence, not negative behavior.

The backend evaluation endpoint is `GET /api/evaluation`. The analysis request accepts `scenario` values `mixed`, `improving`, `declining`, `stable`, and `sudden_change`.
