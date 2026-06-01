import json
import datetime
from typing import List, Dict
from backend.core.models import (
    ConflictIssue, DependencyResult,
    UnusedDependencyResult, ResolvedDependency,
)

def generate_report(service_name, branch_name, conflict_issues,
                    vuln_results, unused_results, all_deps):

    def esc(text):
        if not text:
            return ""
        return (str(text)
                .replace("&",  "&amp;")
                .replace("<",  "&lt;")
                .replace(">",  "&gt;")
                .replace('"',  "&quot;")
                .replace("'",  "&#39;"))

    # ── Pull CSS and JS OUT of .format() entirely ──────────────────────────
    CSS = """
<style>
:root { --bg: #060a12; --surface: #0d1117; --border: #1e293b;
        --text: #e2e8f0; --muted: #475569; --accent: #3b82f6; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "DM Sans", sans-serif; background: var(--bg);
       color: var(--text); min-height: 100vh; }
code { font-family: "Space Mono", monospace; }
#loading-overlay { position: fixed; inset: 0; z-index: 9999;
  background: var(--bg); display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 24px;
  transition: opacity 0.6s ease, visibility 0.6s ease; }
#loading-overlay.hidden { opacity: 0; visibility: hidden; }
.loader-ring { width: 64px; height: 64px; border: 3px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loader-dots { display: flex; gap: 8px; }
.loader-dots span { width: 6px; height: 6px; background: var(--accent);
  border-radius: 50%; animation: pd 1.2s ease-in-out infinite; }
.loader-dots span:nth-child(2) { animation-delay: 0.2s; }
.loader-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes pd {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40%           { transform: scale(1);   opacity: 1;   }
}
.loader-text { font-family: "Space Mono", monospace; font-size: 13px;
  color: var(--muted); letter-spacing: 0.1em; }
.loader-status { font-size: 12px; color: var(--accent);
  font-family: "Space Mono", monospace; min-height: 20px; }
.header { background: linear-gradient(180deg, #080c16 0%, var(--bg) 100%);
  border-bottom: 1px solid var(--border); padding: 28px 40px;
  position: sticky; top: 0; z-index: 100; backdrop-filter: blur(12px); }
.header-inner { max-width: 1280px; margin: 0 auto; display: flex;
  align-items: center; justify-content: space-between;
  gap: 20px; flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand-icon { width: 36px; height: 36px;
  background: linear-gradient(135deg, #1d4ed8, #7c3aed);
  border-radius: 8px; display: flex; align-items: center;
  justify-content: center; font-size: 18px; }
.brand-name { font-family: "Space Mono", monospace; font-size: 15px;
  font-weight: 700; }
.brand-sub { font-size: 11px; color: var(--muted); letter-spacing: 0.05em; }
.header-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-chip { background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 14px; }
.meta-chip-label { font-size: 9px; color: var(--muted); font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase; }
.meta-chip-value { font-size: 13px; font-weight: 600;
  font-family: "Space Mono", monospace; margin-top: 2px; }
.stats-bar { border-bottom: 1px solid var(--border);
  padding: 20px 40px; background: var(--bg); }
.stats-inner { max-width: 1280px; margin: 0 auto;
  display: flex; gap: 12px; flex-wrap: wrap; }
.tabs-bar { border-bottom: 1px solid var(--border); padding: 0 40px;
  background: var(--bg); position: sticky; top: 85px; z-index: 99; }
.tabs-inner { max-width: 1280px; margin: 0 auto; display: flex; }
.tab-btn { padding: 16px 24px; cursor: pointer; font-size: 13px;
  font-weight: 600; color: var(--muted); border: none; background: none;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: all 0.2s; font-family: "DM Sans", sans-serif; }
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-count { display: inline-flex; align-items: center;
  justify-content: center; min-width: 20px; height: 20px;
  border-radius: 10px; font-size: 10px; font-weight: 800;
  padding: 0 6px; margin-left: 6px; }
.tab-count.warn   { background: #2d1800; color: #fb923c; }
.tab-count.danger { background: #2d0a0a; color: #f87171; }
.tab-count.ok     { background: #052e16; color: #4ade80; }
.tab-count.info   { background: #1e3a5f; color: #93c5fd; }
.content { max-width: 1280px; margin: 0 auto; padding: 32px 40px; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
.fade-in { animation: fi 0.4s ease forwards; opacity: 0; }
@keyframes fi {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0);   }
}
</style>
"""

    JS = """
<script>
var statuses = [
  "Parsing dependency tree...",
  "Running conflict analysis...",
  "Querying Snyk for vulnerabilities...",
  "Detecting unused dependencies...",
  "Building report...",
  "Done."
];
var si = 0;
var statusEl = document.getElementById("loader-status");
var iv = setInterval(function() {
  si++;
  if (si < statuses.length) {
    statusEl.style.opacity = "0";
    setTimeout(function() {
      statusEl.textContent = statuses[si];
      statusEl.style.opacity = "1";
    }, 200);
  } else {
    clearInterval(iv);
  }
}, 700);

setTimeout(function() {
  document.getElementById("loading-overlay").classList.add("hidden");
}, 4000);

function switchTab(name, el) {
  document.querySelectorAll(".tab-panel").forEach(function(p) {
    p.classList.remove("active");
  });
  document.querySelectorAll(".tab-btn").forEach(function(b) {
    b.classList.remove("active");
  });
  var panel = document.getElementById("tab-" + name);
  panel.classList.add("active");
  panel.classList.remove("fade-in");
  void panel.offsetWidth;
  panel.classList.add("fade-in");
  el.classList.add("active");
}

function updateSelection() {
  var checked = document.querySelectorAll(
    "#tab-unused input[type=checkbox][id^=dep-]:checked"
  );
  document.getElementById("selection-count").textContent =
    checked.length + " dependenc" + (checked.length === 1 ? "y" : "ies") + " selected";
  var btn = document.getElementById("submit-pr-btn");
  btn.disabled = checked.length === 0;
  btn.style.opacity  = checked.length === 0 ? "0.5" : "1";
  btn.style.cursor   = checked.length === 0 ? "not-allowed" : "pointer";
}

function toggleFile(master, gradleId) {
  document.querySelectorAll("#tab-unused input[data-gradle]").forEach(function(cb) {
    var rg = cb.getAttribute("data-gradle")
               .replace(/\//g, "-").replace(/\./g, "-");
    if (rg === gradleId) cb.checked = master.checked;
  });
  updateSelection();
}

function getSelections() {
  var checked = document.querySelectorAll(
    "#tab-unused input[type=checkbox][id^=dep-]:checked"
  );
  var result = {};
  checked.forEach(function(cb) {
    var g = cb.getAttribute("data-gradle");
    if (!result[g]) result[g] = [];
    result[g].push({
      artifact: cb.getAttribute("data-artifact"),
      line:     parseInt(cb.getAttribute("data-line")),
      action:   cb.getAttribute("data-action"),
    });
  });
  return result;
}

function previewDiff() {
  var sel = getSelections();
  if (!Object.keys(sel).length) {
    alert("Select at least one dependency.");
    return;
  }
  var txt = "";
  for (var gp in sel) {
    var deps    = UNUSED_DATA[gp] || [];
    var chosen  = sel[gp];
    var toRemove = chosen.filter(function(s) { return s.action === "remove"; })
                         .map(function(s) { return s.line; });
    var toMove   = chosen.filter(function(s) { return s.action === "move"; })
                         .map(function(s) { return s.line; });
    txt += "--- a/" + gp + "\\n+++ b/" + gp + "\\n";
    deps.forEach(function(dep) {
      if (toRemove.indexOf(dep.line_number) !== -1) {
        txt += "\\n@@ line " + dep.line_number + " @@\\n";
        txt += "-  " + dep.raw_line.trim() + "\\n";
      } else if (toMove.indexOf(dep.line_number) !== -1) {
        var nl = dep.raw_line.replace(dep.configuration, "testImplementation");
        txt += "\\n@@ line " + dep.line_number + " @@\\n";
        txt += "-  " + dep.raw_line.trim() + "\\n";
        txt += "+  " + nl.trim() + "\\n";
      }
    });
    txt += "\\n";
  }
  document.getElementById("diff-content").textContent = txt;
  document.getElementById("diff-modal").style.display = "flex";
}

function closeDiff() {
  document.getElementById("diff-modal").style.display = "none";
}

function confirmSubmit() {
  closeDiff();
  submitPR();
}

function submitPR() {
  var sel    = getSelections();
  var branch = document.getElementById("pr-branch-input").value.trim();
  if (!branch) { alert("Enter a PR branch name."); return; }
  if (!Object.keys(sel).length) { alert("Select at least one dependency."); return; }
  document.getElementById("pr-payload").value = JSON.stringify({
    selections: sel,
    pr_branch:  branch,
  });
  alert("Selection captured!\\nRun the PR submission step in the app.\\nBranch: " + branch);
}
</script>
<input type="hidden" id="pr-payload" value="">
"""

    # ── NOW build HTML using simple string concatenation — no .format() on CSS/JS
    now         = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    external    = [d for d in all_deps if not d.is_root]
    total_deps  = len(set(d.ga for d in external))
    total_conf  = len(conflict_issues)
    total_vuln  = sum(1 for r in vuln_results if r.is_vulnerable)
    total_clean = sum(1 for r in vuln_results if not r.is_vulnerable)
    vulnerable  = [r for r in vuln_results if r.is_vulnerable and r.vulnerabilities]
    clean       = [r for r in vuln_results if not r.is_vulnerable]
    total_unused     = sum(1 for rs in unused_results.values() for r in rs if r.is_unused)
    total_test_only  = sum(1 for rs in unused_results.values() for r in rs if r.is_test_only)

    # ... rest of your card/section building code (unchanged) ...

    # ── Final assembly — CSS and JS injected directly, no .format() on them ───
    html = (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8">'
        '<title>dependency_refractor &mdash; ' + esc(service_name) + '</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700'
        '&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">'
        + CSS +                          # ← injected directly, no .format()
        '</head><body>'
        + loading_overlay_html           # build these as plain concatenation
        + header_html
        + stats_html
        + tabs_html
        + content_html
        + footer_html
        + JS                             # ← injected directly, no .format()
        + '</body></html>'
    )

    return html
    