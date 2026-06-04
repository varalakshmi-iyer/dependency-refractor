# 🔧 dependency_refractor

> Automated dependency intelligence platform for Java/Gradle microservice ecosystems.

dependency_refractor analyses your Java projects for version conflicts, known vulnerabilities, and unused dependencies — and propagates fixes across your entire service portfolio with a single click.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Use Cases](#use-cases)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Integrations](#integrations)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Overview

In large Java ecosystems with dozens of microservices, dependency hygiene is one of the hardest problems to maintain at scale. The same vulnerable library gets pulled in at different versions across 40 services, unused dependencies accumulate silently across refactors, and fixing one service means manually repeating the same change everywhere else.

dependency_refractor solves this by combining static analysis, Snyk vulnerability intelligence, and GitHub automation into a single workflow — from detecting a problem to raising a fix PR across your entire portfolio.

---

## Use Cases

### ⚡ 1. Conflict Analysis with Snyk-Powered Resolution

In multi-module Java projects, transitive dependencies silently collide — Gradle picks a winner without telling you, and the losing version can break your runtime in ways that are nearly impossible to trace. dependency_refractor surfaces every conflict, cross-references each version against Snyk's vulnerability database, and tells the developer exactly which version to pin — turning a hidden runtime risk into a single, security-informed decision.

**Input:** Gradle build log (`pkg:mvn` format) + GitHub repo  
**Output:** Every conflicting dependency with all versions, Snyk vulnerability status per version, and a recommended safe version to pin

---

### 💀 2. Unused Dependency Detection with Automated PR

Every refactor leaves behind dependencies nobody imports anymore — dead weight that bloats the build, widens the attack surface, and accumulates silently across every `build.gradle` in the project. dependency_refractor cross-references every declared dependency against actual Java import usage across all submodules, and delivers the cleanup as a ready-to-merge pull request — zero manual effort, one click to a leaner, safer build.

**Input:** GitHub repo URL + branch  
**Output:** Interactive list of unused/test-only deps per `build.gradle`, diff preview, configurable PR submission

---

### 🚨 3. Vulnerability Scanning with Snyk

Finding vulnerable dependencies is only half the problem — the other half is doing it consistently across a portfolio of services built on the same stack. dependency_refractor scans every dependency in the tree against Snyk, surfacing CVEs with severity and fix versions. More importantly, it treats one repo as a baseline — so when a vulnerable pattern is identified there, the same fix propagates to every similar service automatically, turning a one-off security fix into an org-wide remediation.

**Input:** Gradle build log  
**Output:** Every vulnerable dependency with CVE IDs, CVSS scores, severity ratings, and safe upgrade versions

---

### 🔄 4. Cross-Repo Fix Propagation

When a developer fixes 15-20 vulnerable dependencies in one service, the same libraries exist across dozens of other repos running the same framework. dependency_refractor captures the fix delta from the source analysis, scans all target repos to find which ones are affected, shows a preview dashboard for the developer to review, and raises one targeted PR per repo — automatically, with no repeated manual work.

**Input:** Source repo analysis + `~` delimited `.txt` file of target repo URLs  
**Output:** Per-repo fix preview dashboard + one PR per selected repo with all applicable version upgrades

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                    │
│         Input Form → Progress → Report + Propagation    │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────┐
│                     FastAPI Backend                      │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Log Parser  │  │   Analyzers  │  │  Propagation  │  │
│  │ pkg:mvn fmt │  │ Conflict     │  │  Engine       │  │
│  └─────────────┘  │ Vuln         │  └───────────────┘  │
│                   │ Unused       │                      │
│                   └──────┬───────┘                      │
└──────────────────────────┼──────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌──────▼──────┐  ┌─────▼──────┐
    │   Snyk    │   │   GitHub    │  │ OC Client  │
    │  REST API │   │  REST API   │  │ subprocess │
    └───────────┘   └─────────────┘  └────────────┘
```

---

## Project Structure

```
dependency_refractor/
│
├── backend/
│   ├── main.py                        # FastAPI app + all routes
│   ├── config.py                      # Settings from .env
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py                  # All dataclasses
│   │   ├── log_fetcher.py             # OC client + file upload handler
│   │   ├── log_parser.py              # pkg:mvn build log parser
│   │   ├── gradle_parser.py           # build.gradle parser
│   │   ├── snyk_client.py             # Snyk REST API client
│   │   ├── github_client.py           # GitHub REST API client
│   │   ├── conflict_analyzer.py       # Version conflict detection
│   │   ├── vulnerability_analyzer.py  # Snyk vulnerability scanning
│   │   ├── unused_analyzer.py         # Unused dependency detection
│   │   ├── pr_submitter.py            # GitHub PR creation
│   │   ├── fix_delta_extractor.py     # Extracts fix recommendations
│   │   ├── propagation_engine.py      # Cross-repo fix propagation
│   │   └── repo_file_parser.py        # ~ delimited repo list parser
│   │
│   ├── report/
│   │   └── html_generator.py          # Full HTML report generator
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── app.py                         # Streamlit UI
│   └── requirements.txt
│
├── .env                               # Secrets — never commit
├── .env.example                       # Template for .env
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.8.8+ | Both backend and frontend |
| Snyk Account | Any tier | API token required |
| GitHub PAT | — | `repo` scope required |
| OpenShift CLI (`oc`) | 4.x+ | Only if using Build ID log fetch |
| Java (optional) | 17+ | Only if running `./gradlew` locally |

---

## Installation

**1. Clone the repo**

```bash
git clone https://github.com/your-org/dependency-refractor.git
cd dependency-refractor
```

**2. Install backend dependencies**

```bash
pip install -r backend/requirements.txt
```

**3. Install frontend dependencies**

```bash
pip install -r frontend/requirements.txt
```

**4. Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your tokens and settings
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```bash
# ── Snyk ───────────────────────────────────────────────
SNYK_TOKEN=your-snyk-personal-access-token
SNYK_ORG_ID=your-snyk-org-id
# Find org ID: Snyk Dashboard → Settings → General → Organization ID

# ── GitHub ─────────────────────────────────────────────
GITHUB_PAT=your-github-personal-access-token
# Required scope: repo (full control of private repositories)

# ── Network (Corporate Proxy) ───────────────────────────
PROXY_URL=http://proxy.internal.yourorg.com:8080
SSL_CERT=/path/to/your-org-ca-bundle.pem
# SSL_CERT can be: true (default) | false (insecure) | /path/to/cert.pem

# ── Snyk Performance ───────────────────────────────────
SNYK_TIMEOUT=90
SNYK_MAX_WORKERS=3
SNYK_MAX_RETRIES=2
SNYK_RETRY_DELAY=3

# ── Fix Propagation ─────────────────────────────────────
TARGET_REPOS_BRANCH=main
PROPAGATE_PR_BRANCH_PREFIX=dependency-refractor/propagate-fixes

# ── App ────────────────────────────────────────────────
BACKEND_URL=http://localhost:8000
```

### GitHub PAT Permissions

The GitHub PAT needs the following scopes:

| Scope | Reason |
|---|---|
| `repo` | Read `build.gradle` and `.java` files |
| `repo` | Create branches and commits |
| `repo` | Open pull requests |

### Snyk API Token

1. Log in to [app.snyk.io](https://app.snyk.io)
2. Go to **Account Settings → General → Auth Token**
3. Copy the token into `SNYK_TOKEN`
4. Go to **Settings → General** to find your **Organization ID** for `SNYK_ORG_ID`

---

## Running the Application

### Option 1 — Local (recommended for development)

```bash
# Terminal 1 — Start backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Start frontend
streamlit run frontend/app.py
```

Open [http://localhost:8501](http://localhost:8501)

### Option 2 — Docker Compose

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

---

## Usage Guide

### Step 1 — Prepare your build log

The build log must be in `pkg:mvn` format, produced by Snyk or a compatible SCA tool:

```
pkg:mvn/com.example/my-service@2.1.0?type=jar -> UNKNOWN
-  pkg:mvn/org.springframework.boot/spring-boot-starter-web@3.2.0?type=jar -> NONE
-  -  pkg:mvn/com.fasterxml.jackson.core/jackson-databind@2.14.0?type=jar -> NONE
```

**Two ways to provide the log:**

| Method | When to use |
|---|---|
| Upload `.log` or `.txt` file | You already have the log |
| Build ID via OC Client | Log is in OpenShift build history |

### Step 2 — Fill in the input form

| Field | Description |
|---|---|
| GitHub Repository URL | `https://github.com/your-org/your-repo` |
| Branch Name | Branch to analyse and base PRs on |
| Service Name | Label shown in the report header |
| Build Log Source | Upload file or provide OpenShift Build ID |
| PR Branch Name | Branch name for unused dep removal PRs |
| Target Repos File | `.txt` file for cross-repo propagation (optional) |
| Target Repos Branch | Branch to read from in target repos |

### Step 3 — Click Analyze

The tool runs all three analyses in parallel:

1. **Conflict Analysis** — with Snyk version recommendations
2. **Vulnerability Scan** — full CVE list per dependency
3. **Unused Detection** — cross-referenced against Java imports

### Step 4 — Review the Report

The HTML report has three tabs:

| Tab | Contents |
|---|---|
| ⚡ Conflict Analysis | Every version conflict, Snyk recommendation, CVE table per version |
| 🚨 Vulnerability Scan | All vulnerable deps with CVE IDs, CVSS scores, upgrade paths |
| 💀 Unused Dependencies | Interactive checklist, diff preview, PR submission |

### Step 5 — Propagate Fixes (optional)

If you uploaded a target repos file:

1. Switch to the **Fix Propagation** tab in Streamlit
2. Click **Scan Target Repos**
3. Review which repos need fixes and what will change
4. Select repos and click **Propagate Fixes**
5. One PR per repo is raised automatically

### Target Repos File Format

Create a `.txt` file with repo URLs separated by `~`:

```
https://github.com/your-org/service-b~https://github.com/your-org/service-c~https://github.com/your-org/service-d
```

Multi-line is also supported:

```
https://github.com/your-org/service-b~https://github.com/your-org/service-c
~https://github.com/your-org/service-d~https://github.com/your-org/service-e
```

---

## API Reference

The FastAPI backend exposes a full REST API. Interactive docs available at `http://localhost:8000/docs`.

### Analysis

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze/upload` | Submit analysis with uploaded build log |
| `POST` | `/analyze/build-id` | Submit analysis using OC Client build ID |
| `GET` | `/job/{job_id}` | Poll job status and progress |
| `GET` | `/job/{job_id}/report` | Fetch completed HTML report |
| `GET` | `/job/{job_id}/debug` | Debug job state |

### Propagation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/propagate/scan` | Scan target repos for applicable fixes |
| `GET` | `/propagate/scan/{id}/status` | Poll scan status and repo summaries |
| `POST` | `/propagate/submit` | Submit PRs to selected repos |
| `GET` | `/propagate/submit/{id}/status` | Poll PR submission status |

### PR Submission

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/pr/submit` | Submit unused dependency removal PR |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend health check |

---

## Integrations

### Snyk

- Used for vulnerability data per dependency version
- Called concurrently with configurable worker count to manage rate limits
- Automatic retry with backoff on timeout or rate limit (429)
- Requires a paid or free Snyk account with API access

### GitHub

- Reads `build.gradle` and `.java` source files via Contents API
- Creates branches, commits modified files, and opens pull requests
- Supports multi-module repos with multiple `build.gradle` files
- Requires a PAT with `repo` scope

### OpenShift (`oc` client)

- Fetches build logs from OpenShift build history via subprocess
- Command template is configurable in `log_fetcher.py`
- Falls back gracefully if `oc` is not on PATH

---

## Known Limitations

| Limitation | Detail |
|---|---|
| Build log format | Only `pkg:mvn` format supported. Standard `./gradlew dependencies` output requires a format adapter |
| Kotlin DSL | `build.gradle.kts` not yet supported — Groovy DSL only |
| Unused detection | Relies on static import analysis. Reflection-based usage and Spring bean injection may produce false positives |
| Snyk rate limits | Free tier: 5 req/30s. Set `SNYK_MAX_WORKERS=1` if hitting limits |
| Java version | OC-based log fetch requires Java 17 on the build agent. Use SDKMAN to manage locally without changing system env |
| In-memory job store | Jobs are lost on backend restart. For production, replace `JOBS` dict with Redis |

---

## Roadmap

| Feature | Status |
|---|---|
| `build.gradle.kts` (Kotlin DSL) support | Planned |
| Maven `pom.xml` support | Planned |
| Python / Node.js ecosystem support | Planned |
| Upgrade path planner with LLM-powered changelog summarisation | Planned |
| Redis-backed job store for production deployments | Planned |
| Deprecation tracker (abandoned / deprecated libraries) | Planned |
| CI/CD pipeline plugin (GitHub Actions, Jenkins) | Planned |
| Org-wide dependency policy enforcement (block PRs with critical CVEs) | Planned |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built to make dependency hygiene a solved problem, not a recurring fire.*
