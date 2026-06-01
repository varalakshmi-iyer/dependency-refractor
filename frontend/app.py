import time
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
  /* Global */
  [data-testid="stAppViewContainer"] {
    background: #060a12;
    color: #e2e8f0;
  }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"] { background: #0d1117; }

  /* Hide streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }

  /* Card containers */
  .dr-card {
    background: #0d1117;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
  }

  /* Inputs */
  .stTextInput > div > div > input,
  .stSelectbox > div > div > div {
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

  /* Buttons */
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

  /* Reset button */
  .reset-btn > button {
    background: #0d1117 !important;
    border: 1px solid #334155 !important;
    color: #94a3b8 !important;
  }

  /* Progress */
  .stProgress > div > div {
    background: linear-gradient(90deg, #1d4ed8, #7c3aed) !important;
  }

  /* Radio */
  .stRadio > div { gap: 8px !important; }
  .stRadio > div > label {
    background: #0d1117 !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    color: #e2e8f0 !important;
    cursor: pointer !important;
  }

  /* File uploader */
  [data-testid="stFileUploader"] {
    background: #0d1117 !important;
    border: 1px dashed #334155 !important;
    border-radius: 8px !important;
  }

  /* Divider */
  hr { border-color: #1e293b !important; }

  /* Alert boxes */
  .stAlert { border-radius: 8px !important; }

  /* Download button */
  [data-testid="stDownloadButton"] > button {
    background: #052e16 !important;
    border: 1px solid #166534 !important;
    color: #4ade80 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div style="padding:32px 0 24px 0;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
        <div style="width:44px;height:44px;background:linear-gradient(135deg,#1d4ed8,#7c3aed);
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


# ── Input form ─────────────────────────────────────────────────────────────────
def render_input_form():
    render_header()

    st.markdown("""
    <div style="max-width:680px;margin:0 auto;">
      <div style="font-size:24px;font-weight:800;color:#f1f5f9;margin-bottom:8px;">
        Start Analysis
      </div>
      <div style="font-size:14px;color:#475569;margin-bottom:32px;">
        Enter your repository details and build log source to begin.
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown('<div class="dr-card">', unsafe_allow_html=True)

            # ── Repository details ─────────────────────────────────────────
            st.markdown(
                '<div style="font-size:13px;font-weight:700;color:#3b82f6;'
                'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">'
                '&#128279; Repository</div>',
                unsafe_allow_html=True,
            )

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

            # ── Build log source ───────────────────────────────────────────
            st.markdown(
                '<div style="font-size:13px;font-weight:700;color:#3b82f6;'
                'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">'
                '&#128196; Build Log Source</div>',
                unsafe_allow_html=True,
            )

            log_source = st.radio(
                "How would you like to provide the build log?",
                options=["Build ID (OC Client)", "Upload File"],
                key="log_source",
                horizontal=True,
            )

            build_id   = None
            namespace  = None
            log_file   = None

            if log_source == "Build ID (OC Client)":
                build_id  = st.text_input(
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

            # ── PR settings ────────────────────────────────────────────────
            st.markdown(
                '<div style="font-size:13px;font-weight:700;color:#3b82f6;'
                'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">'
                '&#128295; PR Settings</div>',
                unsafe_allow_html=True,
            )

            pr_branch = st.text_input(
                "PR Branch Name",
                value="dependency-refractor/remove-unused",
                key="pr_branch",
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Analyze button ─────────────────────────────────────────────
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


# ── Submit analysis ────────────────────────────────────────────────────────────
def submit_analysis(inputs):
    # type: (dict) -> str
    """Submits analysis request to FastAPI. Returns job_id."""
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


# ── Poll for job status ────────────────────────────────────────────────────────
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
        return {"status": "error", "progress": str(e)}


# ── Fetch report HTML ──────────────────────────────────────────────────────────
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
        return "<h1>Error fetching report: {}</h1>".format(e)


# ── Progress screen ────────────────────────────────────────────────────────────
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
    step_map     = {
        "Parsing dependency tree...":          10,
        "Running conflict analysis...":        30,
        "Running vulnerability scan...":       60,
        "Detecting unused dependencies...":    80,
        "Generating report...":                95,
        "Complete":                           100,
    }

    while True:
        job = poll_job(job_id)
        status   = job.get("status", "")
        progress = job.get("progress", "Working...")

        pct = step_map.get(progress, 50)
        progress_bar.progress(pct)
        status_text.markdown(
            '<div style="text-align:center;font-family:monospace;'
            'font-size:13px;color:#3b82f6;margin-top:8px;">{}</div>'.format(progress),
            unsafe_allow_html=True,
        )

        if status == "done":
            progress_bar.progress(100)
            st.session_state["report_html"] = fetch_report(job_id)
            st.session_state["view"]        = "report"
            st.rerun()
            break

        elif status == "error":
            st.error("Analysis failed: {}".format(progress))
            if st.button("Reset"):
                st.session_state["view"] = "input"
                st.rerun()
            break

        time.sleep(2)


# ── Report screen ──────────────────────────────────────────────────────────────
def render_report():
    html = st.session_state.get("report_html", "")

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

    # ── Render HTML report in iframe ───────────────────────────────────────────
    st.components.v1.html(html, height=900, scrolling=True)


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
                    st.session_state["job_id"] = job_id
                    st.session_state["view"]   = "progress"
                    st.rerun()

    elif view == "progress":
        render_progress(st.session_state.get("job_id", ""))

    elif view == "report":
        render_report()


if __name__ == "__main__":
    main()