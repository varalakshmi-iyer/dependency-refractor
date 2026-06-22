import time
import base64
import requests
import streamlit as st
import streamlit.components.v1 as components

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

  .stCheckbox > label {
    color: #e2e8f0 !important;
  }

  .stExpander {
    background: #0d1117 !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _stat_card(icon, value, label, color):
    # type: (str, int, str, str) -> str
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

    # ── Fix Propagation ────────────────────────────────────────────────────────
    _section_title("&#128257; Fix Propagation (Optional)")

    st.markdown(
        '<div style="font-size:12px;color:#475569;margin-bottom:12px;">'
        'Upload a <code>~</code> delimited <code>.txt</code> file of GitHub repo URLs '
        'to propagate vulnerability fixes across multiple services after analysis.'
        '</div>',
        unsafe_allow_html=True,
    )

    target_repos_file = st.file_uploader(
        "Target Repos File (.txt) — ~ delimited GitHub URLs",
        type=["txt"],
        key="target_repos_file",
    )
    target_repos_branch = st.text_input(
        "Target Repos Branch",
        value="main",
        key="target_repos_branch",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Analyze Button ─────────────────────────────────────────────────────────
    analyze_clicked = st.button("&#128270;  Analyze", key="analyze_btn")

    st.markdown('</div>', unsafe_allow_html=True)

    return {
        "repo_url":            repo_url,
        "branch_name":         branch_name,
        "service_name":        service_name,
        "log_source":          log_source,
        "build_id":            build_id,
        "namespace":           namespace,
        "log_file":            log_file,
        "pr_branch":           pr_branch,
        "target_repos_file":   target_repos_file,
        "target_repos_branch": target_repos_branch,
        "clicked":             analyze_clicked,
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


# ── Poll Job Status ────────────────────────────────────────────────────────────
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
        return "<h1 style='color:#f87171;font-family:monospace;padding:40px;'>Error fetching report: {}</h1>".format(e)


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
                for err in errors:
                    st.caption("⚠️ {}".format(err))
            st.session_state["report_html"] = fetch_report(job_id)
            st.session_state["view"]        = "report"
            st.rerun()
            break

        elif status == "error":
            st.error("❌ Analysis failed: {}".format(progress))
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
        return {"status": "error", "progress": str(e), "summaries": [], "errors": [str(e)]}


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
        return {"status": "error", "progress": str(e), "pr_urls": {}, "errors": [str(e)]}


# ── Propagation Tab ────────────────────────────────────────────────────────────
def render_propagation_tab(source_job_id):
    # type: (str) -> None

    target_repos_content = st.session_state.get("target_repos_content", "")
    target_repos_branch  = st.session_state.get("target_repos_branch", "main")

    if not target_repos_content:
        st.markdown(
            '<div style="text-align:center;padding:60px 40px;color:#475569;">'
            '<div style="font-size:48px;margin-bottom:16px;">&#128196;</div>'
            '<div style="font-size:18px;font-weight:700;color:#64748b;">'
            'No target repos file provided</div>'
            '<div style="font-size:13px;margin-top:8px;">'
            'Upload a <code>~</code> delimited <code>.txt</code> file of GitHub repo URLs '
            'on the input screen to enable cross-repo fix propagation.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div style="font-size:14px;font-weight:700;color:#64748b;'
        'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:20px;">'
        '&#128257; FIX PROPAGATION DASHBOARD</div>',
        unsafe_allow_html=True,
    )

    # ── Step 1: Trigger scan ───────────────────────────────────────────────────
    scan_job_id = st.session_state.get("propagation_scan_job_id")

    if not scan_job_id:
        st.markdown(
            '<div style="background:#0d1117;border:1px solid #1e293b;'
            'border-radius:12px;padding:24px;margin-bottom:20px;">'
            '<div style="font-size:14px;color:#e2e8f0;margin-bottom:8px;font-weight:600;">'
            'Ready to propagate fixes</div>'
            '<div style="font-size:13px;color:#475569;margin-bottom:12px;">'
            'Scan all target repos to find which ones have the same vulnerable '
            'dependencies and need the fixes from your source analysis.'
            '</div>'
            '<div style="font-size:12px;color:#64748b;">'
            'Target branch: <code style="color:#93c5fd;">'
            + target_repos_branch +
            '</code></div></div>',
            unsafe_allow_html=True,
        )

        if st.button("&#128270; Scan Target Repos", key="scan_repos_btn"):
            try:
                resp = requests.post(
                    "{}/propagate/scan".format(BACKEND_URL),
                    json={
                        "source_job_id":     source_job_id,
                        "target_branch":     target_repos_branch,
                        "repo_file_content": target_repos_content,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                st.session_state["propagation_scan_job_id"] = resp.json()["scan_job_id"]
                st.rerun()
            except Exception as e:
                st.error("Scan request failed: {}".format(e))
        return

    # ── Poll scan ──────────────────────────────────────────────────────────────
    scan_data = _poll_propagation_scan(scan_job_id)

    if scan_data["status"] == "running":
        st.info("&#9203; {}".format(scan_data.get("progress", "Scanning repos...")))
        time.sleep(2)
        st.rerun()
        return

    if scan_data["status"] == "error":
        st.error("Scan failed: {}".format(scan_data.get("progress", "Unknown error")))
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("Reset Propagation", key="reset_prop_error"):
            del st.session_state["propagation_scan_job_id"]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── Scan results ───────────────────────────────────────────────────────────
    summaries        = scan_data.get("summaries", [])
    total_repos      = scan_data.get("total_repos", 0)
    repos_with_fixes = scan_data.get("repos_with_fixes", 0)
    already_safe     = sum(1 for s in summaries if not s["has_fixes"] and not s.get("error"))
    errors_count     = sum(1 for s in summaries if s.get("error"))

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(_stat_card("&#128196;", total_repos, "TOTAL REPOS", "#e2e8f0"),
                    unsafe_allow_html=True)
    with col2:
        st.markdown(_stat_card("&#9889;", repos_with_fixes, "NEED FIXES",
                               "#ff8c00" if repos_with_fixes > 0 else "#4ade80"),
                    unsafe_allow_html=True)
    with col3:
        st.markdown(_stat_card("&#10003;", already_safe, "ALREADY SAFE", "#4ade80"),
                    unsafe_allow_html=True)
    with col4:
        st.markdown(_stat_card("&#9888;", errors_count, "ERRORS",
                               "#ff4444" if errors_count > 0 else "#4ade80"),
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not summaries:
        st.info("No repos found in the scan result. Check the target repos file format.")
        return

    # ── Repo selection ─────────────────────────────────────────────────────────
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
            checked = st.checkbox(
                "",
                key="repo_check_{}".format(repo_name.replace("/", "_").replace("-", "_")),
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
                    summary.get("branch", target_repos_branch),
                    app_count,
                    safe_count,
                    '<div style="font-size:11px;color:#f87171;margin-top:2px;">'
                    'Error: ' + str(error) + '</div>' if error else "",
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

    # ── Submit / status ────────────────────────────────────────────────────────
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
                st.success("&#10003; {} PR(s) submitted successfully!".format(len(pr_urls)))
                for repo_name, url in pr_urls.items():
                    st.markdown(
                        '&#128279; **{}** — [View PR]({})'.format(repo_name, url)
                    )

            for err in submit_errors:
                st.warning("&#9888; {}".format(err))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("&#8635; Reset Propagation", key="reset_prop_done"):
                for key in ["propagation_scan_job_id", "propagation_submit_job_id"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif submit_data["status"] == "error":
            st.error("Submission failed: {}".format(
                submit_data.get("progress", "Unknown error")
            ))
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("&#8635; Reset Propagation", key="reset_prop_submit_error"):
                for key in ["propagation_scan_job_id", "propagation_submit_job_id"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        col_submit, col_rescan = st.columns([2, 1])

        with col_submit:
            if selected_repos:
                st.markdown(
                    '<div style="font-size:13px;color:#94a3b8;margin-bottom:12px;">'
                    '<strong style="color:#e2e8f0;">{}</strong> repo(s) selected for propagation'
                    '</div>'.format(len(selected_repos)),
                    unsafe_allow_html=True,
                )
                if st.button(
                    "&#10145; Propagate Fixes to {} Repo(s)".format(len(selected_repos)),
                    key="propagate_btn",
                ):
                    try:
                        resp = requests.post(
                            "{}/propagate/submit".format(BACKEND_URL),
                            json={
                                "scan_job_id":    scan_job_id,
                                "selected_repos": selected_repos,
                                "pr_title":       "chore(deps): propagate vulnerability fixes",
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
            if st.button("&#8635; Re-scan Repos", key="rescan_btn"):
                del st.session_state["propagation_scan_job_id"]
                if "propagation_submit_job_id" in st.session_state:
                    del st.session_state["propagation_submit_job_id"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ── Report Screen ──────────────────────────────────────────────────────────────
def render_report():
    html          = st.session_state.get("report_html", "")
    source_job_id = st.session_state.get("job_id", "")

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

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs([
        "&#128196;  Analysis Report",
        "&#128257;  Fix Propagation",
    ])

    with tab1:
        # Render HTML report in base64 iframe — avoids script_runner.py conflicts
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
        render_propagation_tab(source_job_id)


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
                # Store propagation config before file is consumed
                if inputs.get("target_repos_file"):
                    st.session_state["target_repos_content"] = (
                        inputs["target_repos_file"]
                        .read()
                        .decode("utf-8", errors="replace")
                    )
                    st.session_state["target_repos_branch"] = (
                        inputs["target_repos_branch"] or "main"
                    )
                else:
                    st.session_state.pop("target_repos_content", None)
                    st.session_state.pop("target_repos_branch", None)

                job_id = submit_analysis(inputs)
                if job_id:
                    st.session_state["job_id"] = job_id
                    st.session_state["view"]   = "progress"
                    st.rerun()

    elif view == "progress":
        render_progress(st.session_state.get("job_id", ""))

    elif view == "report":
        render_report()


if __name__ == "__main__":
    main()