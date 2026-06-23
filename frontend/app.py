import time
import base64
import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="dependency_refractor",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] {
    background: #060a12;
    color: #e2e8f0;
  }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"] { background: #0d1117; }
  #MainMenu, footer, header { visibility: hidden; }

  .dr-card {
    background: #0d1117;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
  }
  .stTextInput > div > div > input {
    background: #0d1117 !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
  }
  .stTextInput > label,
  .stSelectbox > label,
  .stFileUploader > label,
  .stRadio > label {
    color: #94a3b8 !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
  }
  .stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #7c3aed) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px 32px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.05em !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.85 !important; }
  .reset-btn > button {
    background: #0d1117 !important;
    border: 1px solid #334155 !important;
    color: #94a3b8 !important;
  }
  .stProgress > div > div {
    background: linear-gradient(90deg, #1d4ed8, #7c3aed) !important;
  }
  .stRadio > div { gap: 8px !important; }
  .stRadio > div > label {
    background: #0d1117 !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    color: #e2e8f0 !important;
    cursor: pointer !important;
  }
  [data-testid="stFileUploader"] {
    background: #0d1117 !important;
    border: 1px dashed #334155 !important;
    border-radius: 8px !important;
  }
  hr { border-color: #1e293b !important; }
  .stAlert { border-radius: 8px !important; }
  [data-testid="stDownloadButton"] > button {
    background: #052e16 !important;
    border: 1px solid #166534 !important;
    color: #4ade80 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
  }
  .stTabs [data-baseweb="tab-list"] {
    background: #0d1117 !important;
    border-bottom: 1px solid #1e293b !important;
    gap: 0 !important;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 12px 24px !important;
    border-bottom: 2px solid transparent !important;
  }
  .stTabs [aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom-color: #3b82f6 !important;
    background: transparent !important;
  }
  .stCheckbox > label { color: #e2e8f0 !important; }
  .stExpander {
    background: #0d1117 !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _stat_card(icon, value, label, color):
    # type: (str, object, str, str) -> str
    return (
        '<div style="background:#0d1117;border:1px solid #1e293b;'
        'border-radius:12px;padding:16px;text-align:center;">'
        '<div style="font-size:20px;">{}</div>'
        '<div style="font-size:26px;font-weight:800;color:{};">{}</div>'
        '<div style="font-size:10px;color:#475569;font-weight:700;'
        'letter-spacing:0.1em;margin-top:4px;">{}</div>'
        '</div>'
    ).format(icon, color, value, label)


def _section_title(text):
    # type: (str) -> None
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#3b82f6;'
        'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">'
        + text + '</div>',
        unsafe_allow_html=True,
    )


# ── Header ─────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div style="padding:32px 0 24px 0;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
        <div style="width:44px;height:44px;
                    background:linear-gradient(135deg,#1d4ed8,#7c3aed);
                    border-radius:10px;display:flex;align-items:center;
                    justify-content:center;font-size:22px;">&#128270;</div>
        <div>
          <div style="font-family:'Space Mono',monospace;font-size:22px;
                      font-weight:700;color:#f1f5f9;letter-spacing:-0.02em;">
            dependency_refractor
          </div>
          <div style="font-size:12px;color:#475569;letter-spacing:0.1em;">
            DEPENDENCY SECURITY ANALYSIS PLATFORM
          </div>
        </div>
      </div>
      <hr style="border-color:#1e293b;margin-top:16px;">
    </div>
    """, unsafe_allow_html=True)


# ── Input Form ─────────────────────────────────────────────────────────────────
def render_input_form():
    render_header()

    st.markdown("""
    <div style="max-width:680px;">
      <div style="font-size:24px;font-weight:800;color:#f1f5f9;margin-bottom:8px;">
        Start Analysis
      </div>
      <div style="font-size:14px;color:#475569;margin-bottom:32px;">
        Enter your repository details and build log source to begin.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="dr-card">', unsafe_allow_html=True)

    # ── Repository ─────────────────────────────────────────────────────────────
    _section_title("&#128279; Repository")
    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/your-org/your-repo",
        key="repo_url",
    )
    branch_name = st.text_input(
        "Branch Name",
        placeholder="main",
        key="branch_name",
    )
    service_name = st.text_input(
        "Service Name (for report)",
        placeholder="Payment Service",
        key="service_name",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Build Log ──────────────────────────────────────────────────────────────
    _section_title("&#128196; Build Log Source")
    log_source = st.radio(
        "How would you like to provide the build log?",
        options=["Build ID (OC Client)", "Upload File"],
        key="log_source",
        horizontal=True,
    )

    build_id  = None
    namespace = None
    log_file  = None

    if log_source == "Build ID (OC Client)":
        build_id = st.text_input(
            "Build ID",
            placeholder="my-service-build-123",
            key="build_id",
        )
        namespace = st.text_input(
            "OpenShift Namespace",
            placeholder="default",
            key="namespace",
            value="default",
        )
    else:
        log_file = st.file_uploader(
            "Upload Build Log (.log or .txt)",
            type=["log", "txt"],
            key="log_file",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PR Settings ────────────────────────────────────────────────────────────
    _section_title("&#128295; PR Settings")
    pr_branch = st.text_input(
        "PR Branch Name (for unused dep removal)",
        value="dependency-refractor/remove-unused",
        key="pr_branch",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    analyze_clicked = st.button("&#128270;  Analyze", key="analyze_btn")

    st.markdown('</div>', unsafe_allow_html=True)

    return {
        "repo_url":     repo_url,
        "branch_name":  branch_name,
        "service_name": service_name,
        "log_source":   log_source,
        "build_id":     build_id,
        "namespace":    namespace,
        "log_file":     log_file,
        "pr_branch":    pr_branch,
        "clicked":      analyze_clicked,
    }


# ── Validation ─────────────────────────────────────────────────────────────────
def validate_inputs(inputs):
    # type: (dict) -> list
    errors = []
    if not inputs["repo_url"]:
        errors.append("GitHub Repository URL is required.")
    if not inputs["branch_name"]:
        errors.append("Branch name is required.")
    if inputs["log_source"] == "Build ID (OC Client)" and not inputs["build_id"]:
        errors.append("Build ID is required when using OC Client.")
    if inputs["log_source"] == "Upload File" and not inputs["log_file"]:
        errors.append("Please upload a build log file.")
    return errors


# ── Submit Analysis ────────────────────────────────────────────────────────────
def submit_analysis(inputs):
    # type: (dict) -> str
    try:
        if inputs["log_source"] == "Build ID (OC Client)":
            resp = requests.post(
                "{}/analyze/build-id".format(BACKEND_URL),
                json={
                    "repo_url":     inputs["repo_url"],
                    "branch_name":  inputs["branch_name"],
                    "build_id":     inputs["build_id"],
                    "namespace":    inputs["namespace"] or "default",
                    "service_name": inputs["service_name"],
                    "pr_branch":    inputs["pr_branch"],
                },
                timeout=30,
            )
        else:
            file_bytes = inputs["log_file"].read()
            resp = requests.post(
                "{}/analyze/upload".format(BACKEND_URL),
                data={
                    "repo_url":     inputs["repo_url"],
                    "branch_name":  inputs["branch_name"],
                    "service_name": inputs["service_name"],
                },
                files={
                    "log_file": (
                        inputs["log_file"].name,
                        file_bytes,
                        "text/plain",
                    )
                },
                timeout=30,
            )
        resp.raise_for_status()
        return resp.json()["job_id"]
    except Exception as e:
        st.error("Failed to start analysis: {}".format(e))
        return ""


# ── Poll Job ───────────────────────────────────────────────────────────────────
def poll_job(job_id):
    # type: (str) -> dict
    try:
        resp = requests.get(
            "{}/job/{}".format(BACKEND_URL, job_id),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "error", "progress": str(e), "errors": []}


# ── Fetch Report HTML ──────────────────────────────────────────────────────────
def fetch_report(job_id):
    # type: (str) -> str
    try:
        resp = requests.get(
            "{}/job/{}/report".format(BACKEND_URL, job_id),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return (
            "<h1 style='color:#f87171;font-family:monospace;padding:40px;'>"
            "Error fetching report: {}</h1>".format(e)
        )


# ── Fetch Vuln Data ────────────────────────────────────────────────────────────
def fetch_vuln_data(job_id):
    # type: (str) -> dict
    try:
        resp = requests.get(
            "{}/job/{}/vulns".format(BACKEND_URL, job_id),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"enriched_vulns": [], "error": str(e)}


# ── Progress Screen ────────────────────────────────────────────────────────────
def render_progress(job_id):
    render_header()

    st.markdown("""
    <div style="text-align:center;padding:40px 0 24px 0;">
      <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">
        Analysis in Progress
      </div>
      <div style="font-size:14px;color:#475569;">
        This may take a few minutes depending on the number of dependencies.
      </div>
    </div>
    """, unsafe_allow_html=True)

    progress_bar = st.progress(0)
    status_text  = st.empty()
    error_box    = st.empty()

    step_map = {
        "Parsing dependency tree...":        10,
        "Running conflict analysis...":      30,
        "Running vulnerability scan...":     60,
        "Detecting unused dependencies...":  80,
        "Generating report...":              95,
        "Complete":                         100,
    }

    while True:
        job      = poll_job(job_id)
        status   = job.get("status", "")
        progress = job.get("progress", "Working...")
        errors   = job.get("errors", [])

        pct = step_map.get(progress, 50)
        progress_bar.progress(pct)
        status_text.markdown(
            '<div style="text-align:center;font-family:monospace;'
            'font-size:13px;color:#3b82f6;margin-top:8px;">{}</div>'.format(progress),
            unsafe_allow_html=True,
        )

        if errors:
            with error_box.container():
                for err in errors:
                    st.warning("⚠️ {}".format(err))

        if status == "done":
            progress_bar.progress(100)
            if errors:
                st.warning(
                    "Analysis completed with {} warning(s). "
                    "Some sections may be incomplete.".format(len(errors))
                )
            st.session_state["report_html"] = fetch_report(job_id)
            st.session_state["view"]        = "report"
            st.rerun()
            break

        elif status == "error":
            st.error("Analysis failed: {}".format(progress))
            st.markdown(
                '<div style="font-family:monospace;font-size:12px;color:#94a3b8;'
                'padding:16px;background:#0d1117;border:1px solid #1e293b;'
                'border-radius:8px;margin-top:12px;">'
                'Check the FastAPI terminal logs for the full stack trace.'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("Reset and try again", key="reset_after_error"):
                st.session_state["view"] = "input"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            break

        time.sleep(2)


# ── Tab 2: Vulnerability Fix PR ────────────────────────────────────────────────
def render_vuln_fix_tab(source_job_id, repo_url, branch_name):
    # type: (str, str, str) -> None

    st.markdown(
        '<div style="font-size:14px;font-weight:700;color:#64748b;'
        'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:20px;">'
        '&#9888;&#65039; VULNERABILITY FIX PR</div>',
        unsafe_allow_html=True,
    )

    # ── Load vuln data once ────────────────────────────────────────────────────
    if "vuln_data" not in st.session_state:
        with st.spinner("Loading vulnerability data..."):
            data = fetch_vuln_data(source_job_id)
            st.session_state["vuln_data"]         = data.get("enriched_vulns", [])
            st.session_state["vuln_repo_url"]     = data.get("repo_url", repo_url)
            st.session_state["vuln_branch_name"]  = data.get("branch_name", branch_name)

    vuln_data   = st.session_state.get("vuln_data", [])
    vuln_repo   = st.session_state.get("vuln_repo_url", repo_url)
    vuln_branch = st.session_state.get("vuln_branch_name", branch_name)

    vulnerable = [
        d for d in vuln_data
        if d.get("is_vulnerable") and d.get("vulnerabilities")
    ]

    if not vulnerable:
        st.markdown(
            '<div style="text-align:center;padding:80px 40px;color:#4ade80;">'
            '<div style="font-size:56px;">&#128737;</div>'
            '<div style="font-size:20px;font-weight:700;margin-top:16px;">'
            'No vulnerable dependencies found</div>'
            '<div style="font-size:14px;color:#64748b;margin-top:8px;">'
            'All dependencies are clean according to Snyk</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── PR already raised — show result + propagate button ────────────────────
    pr_job_id = st.session_state.get("vuln_pr_job_id")
    pr_done   = st.session_state.get("vuln_pr_done", False)
    pr_url    = st.session_state.get("vuln_pr_url", "")

    if pr_job_id and not pr_done:
        job_data = poll_job(pr_job_id)
        if job_data.get("status") == "running":
            st.info("&#9203; Creating PR on source repo...")
            time.sleep(2)
            st.rerun()
        elif job_data.get("status") == "done":
            st.session_state["vuln_pr_done"]    = True
            st.session_state["vuln_pr_url"]     = job_data.get("pr_url", "")
            st.session_state["vuln_fix_deltas"] = job_data.get("fix_deltas", [])
            st.rerun()
        elif job_data.get("status") == "error":
            st.error("PR creation failed: {}".format(
                job_data.get("progress", "Unknown error")
            ))
            st.session_state.pop("vuln_pr_job_id", None)
            st.rerun()

    if pr_done and pr_url:
        st.success("&#10003; Fix PR raised successfully!")
        st.markdown(
            '&#128279; [View PR on GitHub]({})'.format(pr_url),
        )
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            '<div style="background:#0d1117;border:1px solid #1e3a5f;'
            'border-radius:12px;padding:20px 24px;margin-bottom:20px;">'
            '<div style="font-size:14px;font-weight:700;color:#93c5fd;margin-bottom:8px;">'
            '&#128257; Propagate this fix to other repos</div>'
            '<div style="font-size:13px;color:#475569;">'
            'The same vulnerable dependencies may exist across other services. '
            'Click below to propagate these version fixes to other repositories.'
            '</div></div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "&#128257; Propagate to Other Repos",
            key="goto_propagation_btn",
        ):
            st.session_state["trigger_propagation"] = True
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("&#8635; Reset Fix PR", key="reset_vuln_pr"):
            for k in ["vuln_pr_job_id", "vuln_pr_done", "vuln_pr_url",
                      "vuln_fix_deltas", "trigger_propagation", "vuln_data"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── PR Config ──────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;color:#475569;margin-bottom:20px;">'
        'Review vulnerable dependencies below. Safe versions are pre-filled '
        'from Snyk. Edit any version before raising the PR. '
        'Only direct dependencies declared in <code>build.gradle</code> are shown.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_branch, col_title = st.columns(2)
    with col_branch:
        pr_branch = st.text_input(
            "PR Branch Name",
            value="dependency-refractor/vuln-fixes",
            key="vuln_pr_branch",
        )
    with col_title:
        pr_title = st.text_input(
            "PR Title",
            value="chore(deps): fix vulnerable dependency versions",
            key="vuln_pr_title",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Column headers ─────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:grid;'
        'grid-template-columns:2fr 1fr 1fr 1fr 2fr;'
        'gap:12px;padding:10px 14px;'
        'background:#0a0f1a;border-radius:8px 8px 0 0;'
        'border:1px solid #1e293b;font-size:10px;font-weight:700;'
        'color:#475569;letter-spacing:0.1em;">'
        '<div>DEPENDENCY</div>'
        '<div>CURRENT</div>'
        '<div>SEVERITY</div>'
        '<div>CVEs</div>'
        '<div>FIX VERSION (EDITABLE)</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    SEV_COLOR = {
        "critical": "#ff4444",
        "high":     "#ff8c00",
        "medium":   "#ffd700",
        "low":      "#4fc3f7",
    }

    edited_fixes = []
    order_map    = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    for idx, dep in enumerate(vulnerable):
        ga          = "{}:{}".format(dep["group"], dep["artifact"])
        current_ver = dep["version"]
        safe_ver    = dep.get("safe_version") or current_ver
        vulns       = dep.get("vulnerabilities", [])
        cve_ids     = [v["cve_id"] for v in vulns]
        worst       = (
            sorted(vulns, key=lambda v: order_map.get(v["severity"], 9))[0]
            if vulns else {}
        )
        worst_sev   = worst.get("severity", "unknown")
        sev_color   = SEV_COLOR.get(worst_sev, "#94a3b8")

        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

        with col1:
            st.markdown(
                '<div style="padding:12px 4px;">'
                '<code style="font-size:12px;color:#e2e8f0;">{}</code>'
                '</div>'.format(ga),
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                '<div style="padding:12px 4px;">'
                '<code style="font-size:12px;color:#f87171;">{}</code>'
                '</div>'.format(current_ver),
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                '<div style="padding:12px 4px;">'
                '<span style="padding:2px 8px;border-radius:4px;'
                'font-size:10px;font-weight:800;color:{col};">'
                '{sev}</span>'
                '</div>'.format(col=sev_color, sev=worst_sev.upper()),
                unsafe_allow_html=True,
            )

        with col4:
            cve_display = "<br>".join(cve_ids[:2])
            if len(cve_ids) > 2:
                cve_display += "<br>+{} more".format(len(cve_ids) - 2)
            st.markdown(
                '<div style="padding:12px 4px;font-size:11px;color:#94a3b8;">'
                '{}</div>'.format(cve_display),
                unsafe_allow_html=True,
            )

        with col5:
            new_version = st.text_input(
                "",
                value=safe_ver,
                key="fix_ver_{}_{}".format(
                    idx,
                    ga.replace(":", "_").replace(".", "_").replace("-", "_"),
                ),
                label_visibility="collapsed",
            )

        if new_version and new_version.strip() != current_ver:
            edited_fixes.append({
                "ga":           ga,
                "group":        dep["group"],
                "artifact":     dep["artifact"],
                "from_version": current_ver,
                "to_version":   new_version.strip(),
                "cve_ids":      cve_ids,
                "reason":       "Snyk: {} CVE(s) — {}".format(
                    len(cve_ids),
                    ", ".join(cve_ids[:2]),
                ),
            })

        st.markdown(
            '<hr style="border-color:#0d1117;margin:0;">',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Raise PR button ────────────────────────────────────────────────────────
    if not edited_fixes:
        st.markdown(
            '<div style="color:#475569;font-size:13px;">'
            'No version changes detected. Edit at least one fix version '
            'above to enable PR creation.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div style="font-size:13px;color:#94a3b8;margin-bottom:12px;">'
        '<strong style="color:#e2e8f0;">{}</strong> version fix(es) ready to commit'
        '</div>'.format(len(edited_fixes)),
        unsafe_allow_html=True,
    )

    for fix in edited_fixes:
        st.markdown(
            '`{}` &nbsp;'
            '<span style="color:#f87171;">{}</span>'
            ' &#10145; '
            '<span style="color:#4ade80;">{}</span>'.format(
                fix["ga"],
                fix["from_version"],
                fix["to_version"],
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("&#128640; Raise Fix PR on Source Repo", key="raise_vuln_pr_btn"):
        try:
            resp = requests.post(
                "{}/vuln/raise-pr".format(BACKEND_URL),
                json={
                    "repo_url":    vuln_repo,
                    "branch_name": vuln_branch,
                    "pr_branch":   pr_branch,
                    "pr_title":    pr_title,
                    "fixes":       edited_fixes,
                },
                timeout=30,
            )
            resp.raise_for_status()
            st.session_state["vuln_pr_job_id"] = resp.json()["job_id"]
            st.rerun()
        except Exception as e:
            st.error("Failed to raise PR: {}".format(e))


# ── Propagation Helpers ────────────────────────────────────────────────────────
def _poll_propagation_scan(scan_job_id):
    # type: (str) -> dict
    try:
        resp = requests.get(
            "{}/propagate/scan/{}/status".format(BACKEND_URL, scan_job_id),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {
            "status": "error", "progress": str(e),
            "summaries": [], "errors": [str(e)],
        }


def _poll_propagation_submit(submit_job_id):
    # type: (str) -> dict
    try:
        resp = requests.get(
            "{}/propagate/submit/{}/status".format(BACKEND_URL, submit_job_id),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {
            "status": "error", "progress": str(e),
            "pr_urls": {}, "errors": [str(e)],
        }


# ── Tab 3: Fix Propagation ─────────────────────────────────────────────────────
def render_propagation_tab(source_job_id, vuln_fix_deltas=None):
    # type: (str, list) -> None

    if vuln_fix_deltas is None:
        vuln_fix_deltas = []

    st.markdown(
        '<div style="font-size:14px;font-weight:700;color:#64748b;'
        'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:20px;">'
        '&#128257; FIX PROPAGATION DASHBOARD</div>',
        unsafe_allow_html=True,
    )

    # ── Banner when coming from vuln fix PR ────────────────────────────────────
    if vuln_fix_deltas:
        fixes_summary = " &nbsp;|&nbsp; ".join(
            '<code>{}</code> &#10145; '
            '<span style="color:#4ade80;">{}</span>'.format(
                f["ga"], f["to_version"]
            )
            for f in vuln_fix_deltas[:3]
        )
        if len(vuln_fix_deltas) > 3:
            fixes_summary += " &nbsp;|&nbsp; +{} more".format(
                len(vuln_fix_deltas) - 3
            )
        st.markdown(
            '<div style="background:#0a1a0a;border:1px solid #166534;'
            'border-radius:8px;padding:12px 16px;margin-bottom:20px;">'
            '<div style="font-size:11px;font-weight:700;color:#4ade80;'
            'letter-spacing:0.08em;margin-bottom:6px;">'
            'PROPAGATING FROM VULN FIX PR</div>'
            '<div style="font-size:12px;color:#86efac;">'
            + fixes_summary +
            '</div></div>',
            unsafe_allow_html=True,
        )

    scan_job_id = st.session_state.get("propagation_scan_job_id")

    # ── Step 1: collect inputs and trigger scan ────────────────────────────────
    if not scan_job_id:
        st.markdown(
            '<div style="background:#0d1117;border:1px solid #1e293b;'
            'border-radius:12px;padding:24px;margin-bottom:20px;">'
            '<div style="font-size:14px;color:#e2e8f0;'
            'margin-bottom:8px;font-weight:600;">'
            'Propagate fixes to other services</div>'
            '<div style="font-size:13px;color:#475569;margin-bottom:16px;">'
            'Upload a <code>~</code> delimited <code>.txt</code> file of GitHub '
            'repo URLs. The tool will scan each repo, find matching vulnerable '
            'dependencies, and raise a targeted fix PR per repo.'
            '</div></div>',
            unsafe_allow_html=True,
        )

        target_repos_file = st.file_uploader(
            "Target Repos File (.txt) — ~ delimited GitHub URLs",
            type=["txt"],
            key="target_repos_file_upload",
        )
        target_repos_branch = st.text_input(
            "Target Repos Branch",
            value="main",
            key="target_repos_branch_input",
            help="Branch to read build.gradle from in each target repo",
        )

        if not target_repos_file:
            st.markdown(
                '<div style="color:#475569;font-size:12px;margin-top:8px;">'
                'Upload a .txt file above to enable scanning.</div>',
                unsafe_allow_html=True,
            )
            return

        if st.button("&#128270; Scan Target Repos", key="scan_repos_btn"):
            try:
                content = target_repos_file.read().decode("utf-8", errors="replace")
                if not content.strip():
                    st.error("The uploaded file is empty.")
                    return

                payload = {
                    "target_branch":     target_repos_branch or "main",
                    "repo_file_content": content,
                }

                # Use fix deltas from vuln PR if available,
                # otherwise fall back to source analysis job
                if vuln_fix_deltas:
                    payload["fix_deltas_override"] = vuln_fix_deltas
                else:
                    payload["source_job_id"] = source_job_id

                resp = requests.post(
                    "{}/propagate/scan".format(BACKEND_URL),
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
                st.session_state["propagation_scan_job_id"]  = (
                    resp.json()["scan_job_id"]
                )
                st.session_state["target_repos_branch_used"] = (
                    target_repos_branch or "main"
                )
                st.rerun()
            except Exception as e:
                st.error("Scan request failed: {}".format(e))
        return

    # ── Poll scan ──────────────────────────────────────────────────────────────
    scan_data = _poll_propagation_scan(scan_job_id)

    if scan_data["status"] == "running":
        st.info("&#9203; {}".format(
            scan_data.get("progress", "Scanning repos...")
        ))
        time.sleep(2)
        st.rerun()
        return

    if scan_data["status"] == "error":
        st.error("Scan failed: {}".format(
            scan_data.get("progress", "Unknown error")
        ))
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("Reset Propagation", key="reset_prop_error"):
            st.session_state.pop("propagation_scan_job_id", None)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── Scan results ───────────────────────────────────────────────────────────
    summaries        = scan_data.get("summaries", [])
    total_repos      = scan_data.get("total_repos", 0)
    repos_with_fixes = scan_data.get("repos_with_fixes", 0)
    already_safe     = sum(
        1 for s in summaries if not s["has_fixes"] and not s.get("error")
    )
    errors_count     = sum(1 for s in summaries if s.get("error"))
    target_branch    = st.session_state.get("target_repos_branch_used", "main")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            _stat_card("&#128196;", total_repos, "TOTAL REPOS", "#e2e8f0"),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _stat_card("&#9889;", repos_with_fixes, "NEED FIXES",
                       "#ff8c00" if repos_with_fixes > 0 else "#4ade80"),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _stat_card("&#10003;", already_safe, "ALREADY SAFE", "#4ade80"),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            _stat_card("&#9888;", errors_count, "ERRORS",
                       "#ff4444" if errors_count > 0 else "#4ade80"),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if not summaries:
        st.info("No repos found in scan result. Check the target repos file format.")
        return

    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#94a3b8;'
        'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">'
        'Select repos to propagate fixes to:</div>',
        unsafe_allow_html=True,
    )

    selected_repos = []

    for summary in summaries:
        repo_name  = summary["repo_name"]
        has_fixes  = summary["has_fixes"]
        error      = summary.get("error")
        pr_url     = summary.get("pr_url")
        app_count  = summary.get("applicable_count", 0)
        safe_count = summary.get("already_safe_count", 0)

        col_check, col_info, col_detail = st.columns([0.5, 3.5, 2])

        with col_check:
            already_submitted = bool(pr_url)
            safe_key = (
                repo_name
                .replace("/", "_")
                .replace("-", "_")
                .replace(".", "_")
            )
            checked = st.checkbox(
                "",
                key="repo_chk_{}".format(safe_key),
                value=has_fixes and not already_submitted,
                disabled=not has_fixes or bool(error) or already_submitted,
            )
            if checked and has_fixes and not already_submitted:
                selected_repos.append(repo_name)

        with col_info:
            if error:
                status_icon, status_color = "&#9888;", "#f87171"
            elif pr_url:
                status_icon, status_color = "&#10003;", "#4ade80"
            elif has_fixes:
                status_icon, status_color = "&#9889;", "#ff8c00"
            else:
                status_icon, status_color = "&#10003;", "#4ade80"

            error_row = (
                '<div style="font-size:11px;color:#f87171;margin-top:2px;">'
                'Error: ' + str(error) + '</div>'
            ) if error else ""

            st.markdown(
                '<div style="padding:12px 0;">'
                '<div style="display:flex;align-items:center;gap:8px;">'
                '<span style="color:{};">{}</span>'
                '<code style="font-size:13px;color:#e2e8f0;">{}</code>'
                '</div>'
                '<div style="font-size:11px;color:#475569;margin-top:4px;">'
                'branch: <code style="color:#93c5fd;">{}</code>'
                ' &nbsp;|&nbsp; {} fix(es) applicable'
                ' &nbsp;|&nbsp; {} already safe'
                '</div>'
                '{}'
                '</div>'.format(
                    status_color, status_icon,
                    repo_name,
                    summary.get("branch", target_branch),
                    app_count,
                    safe_count,
                    error_row,
                ),
                unsafe_allow_html=True,
            )

        with col_detail:
            if pr_url:
                st.markdown(
                    '<a href="{}" target="_blank" '
                    'style="color:#4ade80;font-size:12px;text-decoration:none;">'
                    '&#10145; View PR</a>'.format(pr_url),
                    unsafe_allow_html=True,
                )
            elif has_fixes and summary.get("applicable_fixes"):
                with st.expander("Preview {} fix(es)".format(app_count)):
                    for fix in summary["applicable_fixes"]:
                        st.markdown(
                            '`{}` &nbsp;'
                            '<span style="color:#f87171;">{}</span>'
                            ' &#10145; '
                            '<span style="color:#4ade80;">{}</span>'.format(
                                fix["ga"],
                                fix["from_version"],
                                fix["to_version"],
                            ),
                            unsafe_allow_html=True,
                        )
                        if fix.get("cve_ids"):
                            st.caption("CVEs: {}".format(
                                ", ".join(fix["cve_ids"][:3])
                                + ("..." if len(fix["cve_ids"]) > 3 else "")
                            ))

        st.markdown(
            '<hr style="border-color:#0d1117;margin:4px 0;">',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Submit / poll ──────────────────────────────────────────────────────────
    submit_job_id = st.session_state.get("propagation_submit_job_id")

    if submit_job_id:
        submit_data = _poll_propagation_submit(submit_job_id)

        if submit_data["status"] == "running":
            st.info("&#9203; {}".format(
                submit_data.get("progress", "Submitting PRs...")
            ))
            time.sleep(2)
            st.rerun()

        elif submit_data["status"] == "done":
            pr_urls       = submit_data.get("pr_urls", {})
            submit_errors = submit_data.get("errors", [])

            if pr_urls:
                st.success(
                    "&#10003; {} PR(s) submitted successfully!".format(len(pr_urls))
                )
                for rname, url in pr_urls.items():
                    st.markdown(
                        '&#128279; **{}** — [View PR]({})'.format(rname, url)
                    )
            for err in submit_errors:
                st.warning("&#9888; {}".format(err))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("&#8635; Reset Propagation", key="reset_prop_done"):
                for k in ["propagation_scan_job_id", "propagation_submit_job_id"]:
                    st.session_state.pop(k, None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif submit_data["status"] == "error":
            st.error("Submission failed: {}".format(
                submit_data.get("progress", "Unknown error")
            ))
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("&#8635; Reset Propagation", key="reset_prop_sub_err"):
                for k in ["propagation_scan_job_id", "propagation_submit_job_id"]:
                    st.session_state.pop(k, None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        col_submit, col_rescan = st.columns([2, 1])

        with col_submit:
            if selected_repos:
                st.markdown(
                    '<div style="font-size:13px;color:#94a3b8;margin-bottom:12px;">'
                    '<strong style="color:#e2e8f0;">{}</strong> repo(s) selected'
                    '</div>'.format(len(selected_repos)),
                    unsafe_allow_html=True,
                )
                if st.button(
                    "&#10145; Propagate Fixes to {} Repo(s)".format(
                        len(selected_repos)
                    ),
                    key="propagate_btn",
                ):
                    try:
                        resp = requests.post(
                            "{}/propagate/submit".format(BACKEND_URL),
                            json={
                                "scan_job_id":    scan_job_id,
                                "selected_repos": selected_repos,
                                "pr_title": (
                                    "chore(deps): propagate vulnerability fixes"
                                ),
                                "pr_description": (
                                    "Automated vulnerability fix propagation "
                                    "by dependency_refractor.\n\n"
                                    "Fixes identified in source service analysis "
                                    "and applied to this repository."
                                ),
                            },
                            timeout=30,
                        )
                        resp.raise_for_status()
                        st.session_state["propagation_submit_job_id"] = (
                            resp.json()["submit_job_id"]
                        )
                        st.rerun()
                    except Exception as e:
                        st.error("Propagation request failed: {}".format(e))
            else:
                st.markdown(
                    '<div style="color:#475569;font-size:13px;padding:12px 0;">'
                    'Select at least one repo above to propagate fixes.'
                    '</div>',
                    unsafe_allow_html=True,
                )

        with col_rescan:
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("&#8635; Re-scan", key="rescan_btn"):
                st.session_state.pop("propagation_scan_job_id", None)
                st.session_state.pop("propagation_submit_job_id", None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ── Report Screen ──────────────────────────────────────────────────────────────
def render_report():
    html          = st.session_state.get("report_html", "")
    source_job_id = st.session_state.get("job_id", "")
    repo_url      = st.session_state.get("input_repo_url", "")
    branch_name   = st.session_state.get("input_branch_name", "")

    if not html:
        st.error("No report data found. Please run the analysis again.")
        if st.button("Go back", key="go_back_btn"):
            st.session_state["view"] = "input"
            st.rerun()
        return

    # ── Top bar ────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(
            '<div style="font-family:monospace;font-size:18px;font-weight:700;'
            'color:#f1f5f9;padding:16px 0;">&#128270; dependency_refractor</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.download_button(
            label="&#11015; Download Report",
            data=html.encode("utf-8"),
            file_name="dependency_report.html",
            mime="text/html",
            key="download_report",
        )
    with col3:
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("&#8635; Reset", key="reset_btn"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Three tabs ─────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "&#128196;  Analysis Report",
        "&#9888;&#65039;  Vulnerability Fix PR",
        "&#128257;  Fix Propagation",
    ])

    with tab1:
        try:
            encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
            iframe  = (
                '<iframe '
                'src="data:text/html;base64,{encoded}" '
                'width="100%" '
                'height="920px" '
                'style="border:none;border-radius:8px;" '
                'sandbox="allow-scripts allow-same-origin">'
                '</iframe>'
            ).format(encoded=encoded)
            st.markdown(iframe, unsafe_allow_html=True)
        except Exception as e:
            st.error("Report rendering error: {}".format(e))
            st.info(
                "The report was generated successfully. "
                "Use the Download button above to view it in your browser."
            )

    with tab2:
        render_vuln_fix_tab(source_job_id, repo_url, branch_name)

    with tab3:
        render_propagation_tab(
            source_job_id=source_job_id,
            vuln_fix_deltas=st.session_state.get("vuln_fix_deltas", []),
        )


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if "view" not in st.session_state:
        st.session_state["view"] = "input"

    view = st.session_state["view"]

    if view == "input":
        inputs = render_input_form()

        if inputs["clicked"]:
            errors = validate_inputs(inputs)
            if errors:
                for err in errors:
                    st.error(err)
            else:
                job_id = submit_analysis(inputs)
                if job_id:
                    st.session_state["job_id"]            = job_id
                    st.session_state["input_repo_url"]    = inputs["repo_url"]
                    st.session_state["input_branch_name"] = inputs["branch_name"]
                    st.session_state["view"]              = "progress"
                    st.rerun()

    elif view == "progress":
        render_progress(st.session_state.get("job_id", ""))

    elif view == "report":
        render_report()


if __name__ == "__main__":
    main()