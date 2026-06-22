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
import logging
from backend.core.fix_delta_extractor import FixDeltaExtractor
from backend.core.propagation_engine import PropagationEngine, PropagationResult
from backend.core.repo_file_parser import RepoFileParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dependency_refractor")

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
PROPAGATION_JOBS = {}   # type: dict

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
    repo = repo_url.replace("https://github.com/", "").rstrip("/")

    snyk = SnykClient(
        token=settings.SNYK_TOKEN,
        org_id=settings.SNYK_ORG_ID,
        proxy_url=settings.PROXY_URL,
        ssl_verify=settings.ssl_verify,
        timeout=settings.SNYK_TIMEOUT,
        max_retries=settings.SNYK_MAX_RETRIES,
        retry_delay=settings.SNYK_RETRY_DELAY,
    )
    github = GitHubClient(
        pat=settings.GITHUB_PAT,
        repo=repo,
        proxy_url=settings.PROXY_URL,
        ssl_verify=settings.ssl_verify,
        timeout=settings.SNYK_TIMEOUT,
    )
    return snyk, github


# ── Analysis ─────────────────────────────────────────────────────────────────────
def _run_analysis(job_id, log_content, repo_url, branch_name, service_name):
    try:
        logger.info("[{}] Starting — log size: {} bytes".format(
            job_id, len(log_content)
        ))
        JOBS[job_id] = {"status": "running", "progress": "Parsing dependency tree...", "errors": []}

        # ── Parse ──────────────────────────────────────────────────────────
        parser   = BuildLogParser()
        all_deps = parser.parse(log_content)
        external = [d for d in all_deps if not d.is_root]

        logger.info("[{}] Parse result — total: {}, external: {}, root: {}".format(
            job_id, len(all_deps), len(external),
            len([d for d in all_deps if d.is_root])
        ))

        # ── Guard: if no deps parsed, log the first 500 chars of input ────
        if not all_deps:
            logger.warning("[{}] No dependencies parsed. Log preview:\n{}".format(
                job_id, log_content[:500]
            ))
            JOBS[job_id]["errors"].append(
                "No dependencies found in build log. "
                "Check that the log is in pkg:mvn format."
            )

        if not external:
            logger.warning("[{}] No external deps — conflict and vuln analysis will be empty".format(job_id))
            JOBS[job_id]["errors"].append(
                "No external dependencies found — "
                "all entries may be root services (UNKNOWN status). "
                "Conflict and vulnerability tabs will be empty."
            )

        # ── Conflict ───────────────────────────────────────────────────────
        JOBS[job_id]["progress"] = "Running conflict analysis..."
        snyk, github = _make_clients(repo_url)

        try:
            conflict_issues = ConflictAnalyzer(snyk,max_workers=settings.SNYK_MAX_WORKERS).analyze(external)
            logger.info("[{}] Conflicts: {}".format(job_id, len(conflict_issues)))
        except Exception as e:
            logger.error("[{}] Conflict failed: {}".format(job_id, e), exc_info=True)
            conflict_issues = []
            JOBS[job_id]["errors"].append("Conflict analysis error: {}".format(str(e)))

        # ── Vulnerability ──────────────────────────────────────────────────
        JOBS[job_id]["progress"] = "Running vulnerability scan..."
        try:
            vuln_results = VulnerabilityAnalyzer(snyk,max_workers=settings.SNYK_MAX_WORKERS,).analyze(external)
            logger.info("[{}] Vuln results: {}".format(job_id, len(vuln_results)))
        except Exception as e:
            logger.error("[{}] Vuln failed: {}".format(job_id, e), exc_info=True)
            vuln_results = []
            JOBS[job_id]["errors"].append("Vulnerability scan error: {}".format(str(e)))

        # ── Unused ─────────────────────────────────────────────────────────
        JOBS[job_id]["progress"] = "Detecting unused dependencies..."
        try:
            unused_results = UnusedDependencyAnalyzer(github).analyze(branch_name)
            logger.info("[{}] Unused files affected: {}".format(
                job_id, len(unused_results)
            ))
        except Exception as e:
            logger.error("[{}] Unused failed: {}".format(job_id, e), exc_info=True)
            unused_results = {}
            JOBS[job_id]["errors"].append("Unused analysis error: {}".format(str(e)))

        # ── Report ─────────────────────────────────────────────────────────
        JOBS[job_id]["progress"] = "Generating report..."
        try:
            html = generate_report(
                service_name=service_name or repo_url,
                branch_name=branch_name,
                conflict_issues=conflict_issues,
                vuln_results=vuln_results,
                unused_results=unused_results,
                all_deps=all_deps,
            )
        except Exception as e:
            logger.error("[{}] Report generation failed: {}".format(job_id, e), exc_info=True)
            raise

        logger.info("[{}] Done — HTML size: {} bytes".format(job_id, len(html)))
        JOBS[job_id] = {
            "status":   "done",
            "progress": "Complete",
            "html":     html,
            "errors":   JOBS[job_id].get("errors", []),
        }

    except Exception as e:
        logger.error("[{}] Fatal error: {}".format(job_id, e), exc_info=True)
        JOBS[job_id] = {
            "status":   "error",
            "progress": str(e),
            "html":     "",
            "errors":   [str(e)],
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
    if not log_file.filename.endswith((".log", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only .log or .txt files are accepted",
        )

    content     = await log_file.read()
    log_content = LogFetcher().read_uploaded_file(content)

    # ── Debug: confirm content received ────────────────────────────────────
    logger.info("Upload received — filename: {}, size: {} bytes, preview: {}".format(
        log_file.filename,
        len(content),
        log_content[:200].replace("\n", " "),
    ))

    if not log_content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "progress": "Starting analysis...", "errors": []}

    background_tasks.add_task(
        _run_analysis, job_id, log_content,
        repo_url, branch_name, service_name,
    )
    return {"job_id": job_id}

@app.get("/job/{job_id}")
def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status":   job["status"],
        "progress": job.get("progress", ""),
        "errors":   job.get("errors", []),   # ← expose errors to frontend
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


@app.get("/job/{job_id}/debug")
def debug_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Return everything except the full HTML (too large)
    return {
        "status":   job.get("status"),
        "progress": job.get("progress"),
        "errors":   job.get("errors", []),
        "has_html": bool(job.get("html")),
        "html_len": len(job.get("html", "")),
    }


class PropagationScanRequest(BaseModel):
    source_job_id:   str
    target_branch:   str
    repo_file_content: str    # raw text content of the ~ delimited file


class PropagationSubmitRequest(BaseModel):
    scan_job_id:     str
    selected_repos:  List[str]    # list of repo_names to submit PRs for
    pr_title:        Optional[str] = "chore(deps): propagate vulnerability fixes"
    pr_description:  Optional[str] = ""


@app.post("/propagate/scan")
def propagate_scan(req: PropagationScanRequest, background_tasks: BackgroundTasks):
    """
    Step 1 — Scan target repos and compute applicable fixes.
    Reads fix delta from a completed analysis job.
    """
    source_job = JOBS.get(req.source_job_id)
    if not source_job:
        raise HTTPException(status_code=404, detail="Source job not found")
    if source_job.get("status") != "done":
        raise HTTPException(status_code=400, detail="Source job not complete yet")

    scan_job_id = str(uuid.uuid4())
    PROPAGATION_JOBS[scan_job_id] = {
        "status":   "running",
        "progress": "Parsing repo list...",
        "result":   None,
        "errors":   [],
    }

    def run_scan():
        try:
            # Parse repo list
            parser    = RepoFileParser()
            repo_urls = parser.parse(req.repo_file_content)

            if not repo_urls:
                PROPAGATION_JOBS[scan_job_id] = {
                    "status":   "error",
                    "progress": "No valid repo URLs found in file",
                    "result":   None,
                    "errors":   ["No valid repo URLs found in file"],
                }
                return

            PROPAGATION_JOBS[scan_job_id]["progress"] = (
                "Extracting fix delta from source analysis..."
            )

            # Extract fix delta from source job
            # We need the stored conflict and vuln results
            conflict_issues = source_job.get("conflict_issues", [])
            vuln_results    = source_job.get("vuln_results", [])
            fix_deltas      = FixDeltaExtractor().extract(conflict_issues, vuln_results)

            logger.info("Scan job {} — {} fix deltas, {} target repos".format(
                scan_job_id, len(fix_deltas), len(repo_urls)
            ))

            PROPAGATION_JOBS[scan_job_id]["progress"] = (
                "Scanning {} target repos...".format(len(repo_urls))
            )

            # Scan repos
            engine = PropagationEngine(
                github_pat=settings.GITHUB_PAT,
                proxy_url=settings.PROXY_URL,
                ssl_verify=settings.ssl_verify,
                timeout=settings.SNYK_TIMEOUT,
            )
            result = engine.scan_repos(repo_urls, req.target_branch, fix_deltas)

            PROPAGATION_JOBS[scan_job_id] = {
                "status":      "done",
                "progress":    "Scan complete",
                "result":      result,
                "fix_deltas":  fix_deltas,
                "errors":      [],
            }
            logger.info("Propagation scan done — {} repos with fixes".format(
                result.repos_with_fixes
            ))

        except Exception as e:
            logger.error("Propagation scan failed: {}".format(e), exc_info=True)
            PROPAGATION_JOBS[scan_job_id] = {
                "status":   "error",
                "progress": str(e),
                "result":   None,
                "errors":   [str(e)],
            }

    background_tasks.add_task(run_scan)
    return {"scan_job_id": scan_job_id}


@app.get("/propagate/scan/{scan_job_id}/status")
def propagate_scan_status(scan_job_id: str):
    """Poll propagation scan status."""
    job = PROPAGATION_JOBS.get(scan_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    result   = job.get("result")
    summaries = []

    if result:
        for s in result.repo_summaries:
            summaries.append({
                "repo_name":         s.repo_name,
                "repo_url":          s.repo_url,
                "branch":            s.branch,
                "has_fixes":         s.has_fixes,
                "applicable_count":  len(s.applicable_fixes),
                "already_safe_count":len(s.already_safe),
                "not_present_count": len(s.not_present),
                "error":             s.error,
                "status":            s.status,
                "pr_url":            s.pr_url,
                "applicable_fixes": [
                    {
                        "ga":           f.ga,
                        "from_version": f.from_version,
                        "to_version":   f.to_version,
                        "reason":       f.reason,
                        "cve_ids":      f.cve_ids,
                    }
                    for f in s.applicable_fixes
                ],
            })

    return {
        "status":    job["status"],
        "progress":  job.get("progress", ""),
        "errors":    job.get("errors", []),
        "summaries": summaries,
        "total_repos":      result.total_repos      if result else 0,
        "repos_with_fixes": result.repos_with_fixes if result else 0,
    }


@app.post("/propagate/submit")
def propagate_submit(req: PropagationSubmitRequest, background_tasks: BackgroundTasks):
    """
    Step 2 — Submit PRs to selected repos.
    """
    job = PROPAGATION_JOBS.get(req.scan_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail="Scan not complete yet")

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=400, detail="No scan result found")

    submit_job_id = str(uuid.uuid4())
    PROPAGATION_JOBS[submit_job_id] = {
        "status":   "running",
        "progress": "Submitting PRs...",
        "pr_urls":  {},
        "errors":   [],
    }

    def run_submit():
        engine = PropagationEngine(
            github_pat=settings.GITHUB_PAT,
            proxy_url=settings.PROXY_URL,
            ssl_verify=settings.ssl_verify,
            timeout=settings.SNYK_TIMEOUT,
        )
        pr_urls = {}
        errors  = []
        total   = len(req.selected_repos)

        for idx, repo_name in enumerate(req.selected_repos, 1):
            PROPAGATION_JOBS[submit_job_id]["progress"] = (
                "Submitting PR {}/{} — {}".format(idx, total, repo_name)
            )
            # Find summary for this repo
            summary = next(
                (s for s in result.repo_summaries if s.repo_name == repo_name),
                None,
            )
            if not summary or not summary.has_fixes:
                logger.warning("No fixes for repo: {}".format(repo_name))
                continue

            try:
                pr_url = engine.submit_pr(
                    summary=summary,
                    pr_branch_prefix=settings.PROPAGATE_PR_PREFIX,
                    pr_title=req.pr_title,
                    pr_description=req.pr_description,
                )
                pr_urls[repo_name] = pr_url
                summary.pr_url = pr_url
                summary.status = "submitted"
                logger.info("PR submitted for {}: {}".format(repo_name, pr_url))

            except Exception as e:
                logger.error("PR failed for {}: {}".format(repo_name, e), exc_info=True)
                errors.append("PR failed for {}: {}".format(repo_name, str(e)))
                summary.status = "error"
                summary.error  = str(e)

        PROPAGATION_JOBS[submit_job_id] = {
            "status":   "done",
            "progress": "Complete — {} PR(s) submitted".format(len(pr_urls)),
            "pr_urls":  pr_urls,
            "errors":   errors,
        }
        logger.info("Propagation submit done — {} PRs".format(len(pr_urls)))

    background_tasks.add_task(run_submit)
    return {"submit_job_id": submit_job_id}


@app.get("/propagate/submit/{submit_job_id}/status")
def propagate_submit_status(submit_job_id: str):
    """Poll PR submission status."""
    job = PROPAGATION_JOBS.get(submit_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Submit job not found")
    return {
        "status":   job["status"],
        "progress": job.get("progress", ""),
        "pr_urls":  job.get("pr_urls", {}),
        "errors":   job.get("errors", []),
    }