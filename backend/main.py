import os
import uuid
import asyncio
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from backend.config import settings
from backend.core.log_fetcher import LogFetcher
from backend.core.log_parser import BuildLogParser
from backend.core.snyk_client import SnykClient
from backend.core.github_client import GitHubClient
from backend.core.conflict_analyzer import ConflictAnalyzer
from backend.core.vulnerability_analyzer import VulnerabilityAnalyzer
from backend.core.unused_analyzer import UnusedDependencyAnalyzer
from backend.core.pr_submitter import PRSubmitter
from backend.report.html_generator import generate_report

app = FastAPI(
    title="dependency_refractor",
    description="Dependency analysis API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory job store ────────────────────────────────────────────────────────
# In production, replace with Redis or a database
JOBS = {}   # type: dict


class AnalyzeRequest(BaseModel):
    repo_url:    str
    branch_name: str
    build_id:    Optional[str] = None
    service_name: Optional[str] = ""
    namespace:   Optional[str] = "default"
    pr_branch:   Optional[str] = "dependency-refractor/remove-unused"
    pr_title:    Optional[str] = "chore: remove unused dependencies"


class PRRequest(BaseModel):
    repo_url:          str
    branch_name:       str
    pr_branch:         str
    pr_title:          str
    pr_description:    str
    selections_by_file: dict   # { gradle_path: [{ gav, is_unused, is_test_only, ... }] }


def _make_clients(repo_url):
    # type: (str) -> tuple
    """Instantiate all clients from settings."""
    repo = repo_url.replace("https://github.com/", "").rstrip("/")

    snyk = SnykClient(
        token=settings.SNYK_TOKEN,
        org_id=settings.SNYK_ORG_ID,
        proxy_url=settings.PROXY_URL,
        ssl_verify=settings.ssl_verify,
        timeout=settings.SNYK_TIMEOUT,
    )
    github = GitHubClient(
        pat=settings.GITHUB_PAT,
        repo=repo,
        proxy_url=settings.PROXY_URL,
        ssl_verify=settings.ssl_verify,
        timeout=settings.SNYK_TIMEOUT,
    )
    return snyk, github


def _run_analysis(job_id, log_content, repo_url,
                  branch_name, service_name):
    # type: (str, str, str, str, str) -> None
    """Runs full analysis pipeline and stores result in JOBS."""
    try:
        JOBS[job_id] = {"status": "running", "progress": "Parsing dependency tree..."}

        # Parse log
        parser    = BuildLogParser()
        all_deps  = parser.parse(log_content)
        external  = [d for d in all_deps if not d.is_root]

        JOBS[job_id]["progress"] = "Running conflict analysis..."
        snyk, github = _make_clients(repo_url)

        conflict_issues = ConflictAnalyzer(snyk).analyze(external)

        JOBS[job_id]["progress"] = "Running vulnerability scan..."
        vuln_results = VulnerabilityAnalyzer(snyk).analyze(external)

        JOBS[job_id]["progress"] = "Detecting unused dependencies..."
        unused_results = UnusedDependencyAnalyzer(github).analyze(branch_name)

        JOBS[job_id]["progress"] = "Generating report..."
        html = generate_report(
            service_name=service_name or repo_url,
            branch_name=branch_name,
            conflict_issues=conflict_issues,
            vuln_results=vuln_results,
            unused_results=unused_results,
            all_deps=all_deps,
        )

        JOBS[job_id] = {
            "status":   "done",
            "progress": "Complete",
            "html":     html,
        }

    except Exception as e:
        JOBS[job_id] = {
            "status":   "error",
            "progress": str(e),
            "html":     "",
        }


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze/build-id")
def analyze_with_build_id(
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """Fetch build log via OC client, then run analysis."""
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "progress": "Fetching build log via OC..."}

    def run():
        try:
            log_content = LogFetcher().fetch_via_oc(
                build_id=req.build_id,
                namespace=req.namespace,
            )
            _run_analysis(
                job_id, log_content,
                req.repo_url, req.branch_name,
                req.service_name,
            )
        except Exception as e:
            JOBS[job_id] = {"status": "error", "progress": str(e), "html": ""}

    background_tasks.add_task(run)
    return {"job_id": job_id}


@app.post("/analyze/upload")
async def analyze_with_upload(
    background_tasks: BackgroundTasks,
    repo_url:     str = Form(...),
    branch_name:  str = Form(...),
    service_name: str = Form(""),
    log_file:     UploadFile = File(...),
):
    """Accept uploaded .log or .txt build log file, then run analysis."""
    if not log_file.filename.endswith((".log", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only .log or .txt files are accepted",
        )

    content     = await log_file.read()
    log_content = LogFetcher().read_uploaded_file(content)

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "progress": "Starting analysis..."}

    background_tasks.add_task(
        _run_analysis, job_id, log_content,
        repo_url, branch_name, service_name,
    )
    return {"job_id": job_id}


@app.get("/job/{job_id}")
def get_job_status(job_id: str):
    """Poll for job status and progress."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status":   job["status"],
        "progress": job.get("progress", ""),
    }


@app.get("/job/{job_id}/report")
def get_job_report(job_id: str):
    """Fetch the completed HTML report."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job not complete yet")
    return HTMLResponse(content=job["html"])


@app.post("/pr/submit")
def submit_pr(req: PRRequest):
    """Submit a PR to remove/move selected unused dependencies."""
    try:
        _, github = _make_clients(req.repo_url)
        submitter = PRSubmitter(github)

        # Rebuild UnusedDependencyResult objects from the request payload
        # (simplified — selections passed as raw dicts from UI)
        pr_url = submitter.submit_pr(
            selections_by_file=req.selections_by_file,
            base_branch=req.branch_name,
            pr_branch=req.pr_branch,
            pr_title=req.pr_title,
            pr_description=req.pr_description,
        )
        return {"pr_url": pr_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))