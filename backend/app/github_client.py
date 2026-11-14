import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

BASE = "https://api.github.com"


class GitHubClient:
    """Collect developer-level behavioral evidence from a GitHub repository.

    The collector intentionally keeps the raw observations separate from the
    skill inference layer. It returns commits, pull requests, review evidence,
    and issues as normalized events that the feature engine can aggregate.
    """

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "").strip()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(BASE + path, params=params, timeout=30)
        response.raise_for_status()
        return response.json(), response.headers

    def _get_all(self, path: str, params: dict | None = None, max_pages: int = 10):
        """Fetch paginated GitHub results without blindly pulling a huge repo."""
        params = dict(params or {})
        params["per_page"] = min(int(params.get("per_page", 100)), 100)
        items = []

        for page in range(1, max_pages + 1):
            params["page"] = page
            data, headers = self._get(path, params)
            if not isinstance(data, list):
                return data
            items.extend(data)
            if len(data) < params["per_page"] or "next" not in headers.get("Link", ""):
                break
        return items

    @staticmethod
    def _login(obj: dict[str, Any] | None):
        return (obj or {}).get("login")

    @staticmethod
    def _parse_dt(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _within(dt: datetime | None, since: datetime):
        return bool(dt and dt >= since)

    @staticmethod
    def _text(*parts):
        return "\n".join(str(p or "") for p in parts if p)

    @staticmethod
    def _path_counts(files: list[dict]):
        paths = [str(f.get("filename", "")) for f in files if f.get("filename")]
        lower = [p.lower() for p in paths]

        test_files = sum(
            1
            for p in lower
            if (
                "/test/" in p
                or "/tests/" in p
                or p.startswith("test/")
                or p.startswith("tests/")
                or p.endswith(("_test.py", ".test.js", ".test.jsx", ".test.ts", ".test.tsx"))
                or ".spec." in p
                or p.endswith(("Test.java", "Tests.java"))
            )
        )

        security_files = sum(
            1 for p in lower if any(k in p for k in ["auth", "security", "permission", "crypto", "csrf", "sanit"])
        )
        documentation_files = sum(
            1 for p in lower if p.endswith((".md", ".mdx", ".rst", ".adoc")) or "/docs/" in p or p.startswith("docs/")
        )
        concurrency_files = sum(
            1 for p in lower if any(k in p for k in ["thread", "async", "concurr", "worker", "queue", "mutex", "lock"])
        )
        performance_files = sum(
            1 for p in lower if any(k in p for k in ["benchmark", "performance", "profil", "cache", "optimization", "optimi"])
        )
        return {
            "files": paths,
            "test_files_changed": test_files,
            "security_files_changed": security_files,
            "documentation_files_changed": documentation_files,
            "concurrency_files_changed": concurrency_files,
            "performance_files_changed": performance_files,
        }

    def _commit_event(self, owner: str, repo: str, item: dict, username: str | None, since: datetime):
        commit = item.get("commit", {})
        author = self._login(item.get("author")) or (commit.get("author") or {}).get("name")
        if username and (not author or author.lower() != username.lower()):
            return None

        dt = self._parse_dt((commit.get("author") or {}).get("date"))
        if not self._within(dt, since):
            return None

        detail, _ = self._get(f"/repos/{owner}/{repo}/commits/{item.get('sha')}")
        files = detail.get("files", []) if isinstance(detail, dict) else []
        counts = self._path_counts(files)

        return {
            "type": "commit",
            "date": dt.isoformat() if dt else None,
            "message": commit.get("message", ""),
            "author": author,
            "sha": item.get("sha"),
            "files_changed": int(detail.get("files", []) and len(files) or 0),
            "additions": int(detail.get("stats", {}).get("additions", 0) or 0),
            "deletions": int(detail.get("stats", {}).get("deletions", 0) or 0),
            "category_files_changed": sum(
                counts[k] for k in [
                    "security_files_changed",
                    "test_files_changed",
                    "concurrency_files_changed",
                    "documentation_files_changed",
                    "performance_files_changed",
                ]
            ),
            **counts,
            "review_count": 0,
            "correction_count": 0,
            "issue_count": 0,
        }

    def _pull_request_event(self, owner: str, repo: str, item: dict, username: str | None, since: datetime):
        author = self._login(item.get("user"))
        if username and (not author or author.lower() != username.lower()):
            return None

        dt = self._parse_dt(item.get("created_at"))
        if not self._within(dt, since):
            return None

        number = item.get("number")
        files = self._get_all(f"/repos/{owner}/{repo}/pulls/{number}/files", max_pages=5)
        if not isinstance(files, list):
            files = []
        counts = self._path_counts(files)

        reviews = self._get_all(f"/repos/{owner}/{repo}/pulls/{number}/reviews", max_pages=5)
        if not isinstance(reviews, list):
            reviews = []

        review_bodies = []
        correction_count = 0
        for review in reviews:
            body = review.get("body") or ""
            review_bodies.append(body)
            state = str(review.get("state", "")).upper()
            # CHANGES_REQUESTED is a direct review correction signal. We also
            # retain review text so the feature layer can inspect category terms.
            if state == "CHANGES_REQUESTED":
                correction_count += 1

        review_text = "\n".join(review_bodies)
        return {
            "type": "pull_request",
            "date": dt.isoformat() if dt else None,
            "message": self._text(item.get("title"), item.get("body"), review_text),
            "author": author,
            "number": number,
            "files_changed": int(item.get("changed_files", len(files)) or len(files)),
            "additions": int(item.get("additions", 0) or 0),
            "deletions": int(item.get("deletions", 0) or 0),
            "category_files_changed": sum(
                counts[k] for k in [
                    "security_files_changed",
                    "test_files_changed",
                    "concurrency_files_changed",
                    "documentation_files_changed",
                    "performance_files_changed",
                ]
            ),
            **counts,
            "review_count": len(reviews),
            "correction_count": correction_count,
            "issue_count": 0,
        }

    def _issue_event(self, item: dict, username: str | None, since: datetime):
        author = self._login(item.get("user"))
        if username and (not author or author.lower() != username.lower()):
            return None

        dt = self._parse_dt(item.get("created_at"))
        if not self._within(dt, since):
            return None

        labels = [str((label or {}).get("name", "")) for label in item.get("labels", [])]
        closed = self._parse_dt(item.get("closed_at"))
        resolution_hours = None
        if closed and dt:
            resolution_hours = round((closed - dt).total_seconds() / 3600, 2)

        return {
            "type": "issue",
            "date": dt.isoformat() if dt else None,
            "message": self._text(item.get("title"), item.get("body"), " ".join(labels)),
            "author": author,
            "number": item.get("number"),
            "files_changed": 0,
            "additions": 0,
            "deletions": 0,
            "category_files_changed": 0,
            "test_files_changed": 0,
            "security_files_changed": 0,
            "documentation_files_changed": 0,
            "concurrency_files_changed": 0,
            "performance_files_changed": 0,
            "review_count": 0,
            "correction_count": 0,
            "issue_count": 1,
            "labels": labels,
            "resolution_hours": resolution_hours,
        }

    def collect(self, owner: str, repo: str, weeks: int = 8, username: str | None = None):
        if not owner or not repo:
            raise ValueError("Repository owner and name are required.")
        if not username:
            raise ValueError("A GitHub username is required for developer-level analysis.")

        since = datetime.now(timezone.utc) - timedelta(weeks=weeks)

        commits_raw = self._get_all(
            f"/repos/{owner}/{repo}/commits",
            {"since": since.isoformat(), "per_page": 100},
            max_pages=10,
        )
        prs_raw = self._get_all(
            f"/repos/{owner}/{repo}/pulls",
            {"state": "all", "sort": "created", "direction": "desc", "per_page": 100},
            max_pages=10,
        )
        issues_raw = self._get_all(
            f"/repos/{owner}/{repo}/issues",
            {"state": "all", "sort": "created", "direction": "desc", "since": since.isoformat(), "per_page": 100},
            max_pages=10,
        )

        events = []
        for item in commits_raw if isinstance(commits_raw, list) else []:
            event = self._commit_event(owner, repo, item, username, since)
            if event:
                events.append(event)

        for item in prs_raw if isinstance(prs_raw, list) else []:
            event = self._pull_request_event(owner, repo, item, username, since)
            if event:
                events.append(event)

        for item in issues_raw if isinstance(issues_raw, list) else []:
            # GitHub's Issues API includes pull requests; exclude those here.
            if item.get("pull_request"):
                continue
            event = self._issue_event(item, username, since)
            if event:
                events.append(event)

        events.sort(key=lambda x: x.get("date") or "")
        return events


    def contributors(self, owner: str, repo: str, limit: int = 20):
        """Return visible contributors for a repository for profile selection."""
        if not owner or not repo:
            raise ValueError("Repository owner and name are required.")
        items = self._get_all(
            f"/repos/{owner}/{repo}/contributors",
            {"per_page": min(max(int(limit), 1), 100)},
            max_pages=1,
        )
        return [
            {"login": item.get("login"), "contributions": int(item.get("contributions", 0) or 0),
             "avatar_url": item.get("avatar_url"), "html_url": item.get("html_url")}
            for item in (items if isinstance(items, list) else []) if item.get("login")
        ]
