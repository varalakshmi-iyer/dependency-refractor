import json
import datetime
from typing import List, Dict
from backend.core.models import (
    ConflictIssue, DependencyResult,
    UnusedDependencyResult, ResolvedDependency,
)


def generate_report(service_name, branch_name, conflict_issues,
                    vuln_results, unused_results, all_deps):
    # type: (str, str, List[ConflictIssue], List[DependencyResult], Dict[str, List[UnusedDependencyResult]], List[ResolvedDependency]) -> str

    def esc(text):
        # type: (str) -> str
        if not text:
            return ""
        return (str(text)
                .replace("&",  "&amp;")
                .replace("<",  "&lt;")
                .replace(">",  "&gt;")
                .replace('"',  "&quot;")
                .replace("'",  "&#39;"))

    now          = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    external     = [d for d in all_deps if not d.is_root]
    total_deps   = len(set(d.ga for d in external))
    total_conf   = len(conflict_issues)
    total_vuln   = sum(1 for r in vuln_results if r.is_vulnerable)
    total_clean  = sum(1 for r in vuln_results if not r.is_vulnerable)
    vulnerable   = [r for r in vuln_results if r.is_vulnerable and r.vulnerabilities]
    clean        = [r for r in vuln_results if not r.is_vulnerable]
    total_unused = sum(1 for rs in unused_results.values() for r in rs if r.is_unused)
    total_test_only = sum(1 for rs in unused_results.values() for r in rs if r.is_test_only)

    SEV = {
        "critical": ("#ff4444", "#2d0a0a"),
        "high":     ("#ff8c00", "#2d1800"),
        "medium":   ("#ffd700", "#2d2400"),
        "low":      ("#4fc3f7", "#0a1e2d"),
        "CRITICAL": ("#ff4444", "#2d0a0a"),
        "HIGH":     ("#ff8c00", "#2d1800"),
        "MEDIUM":   ("#ffd700", "#2d2400"),
    }

    def sev_badge(sev):
        col, bg = SEV.get(sev.lower(), ("#94a3b8", "#1e293b"))
        return (
            '<span style="padding:3px 10px;border-radius:4px;font-size:10px;'
            'font-weight:800;letter-spacing:0.08em;color:{};background:{};">'
            '{}</span>'.format(col, bg, esc(sev.upper()))
        )

    def cvss_bar(score):
        width = int((float(score) / 10.0) * 100)
        color = (
            "#ff4444" if float(score) >= 9.0 else
            "#ff8c00" if float(score) >= 7.0 else
            "#ffd700" if float(score) >= 4.0 else
            "#4fc3f7"
        )
        return (
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="flex:1;height:4px;background:#1e293b;border-radius:2px;">'
            '<div style="width:{}%;height:100%;background:{};'
            'border-radius:2px;"></div></div>'
            '<span style="font-size:11px;font-weight:700;color:{};">{}</span>'
            '</div>'.format(width, color, color, score)
        )

    def version_chip(v, recommended, vuln_map):
        result   = vuln_map.get(v)
        is_rec   = (v == recommended)
        is_vuln  = result.is_vulnerable if result else False
        num_cves = len(result.vulnerabilities) if result else 0
        if is_rec and not is_vuln:
            return (
                '<span style="padding:4px 12px;border-radius:6px;'
                'border:1px solid #22c55e;background:#052e16;'
                'color:#4ade80;font-size:12px;font-family:monospace;margin:3px;'
                'display:inline-block;">&#10003; {}</span>'.format(esc(v))
            )
        elif is_vuln:
            return (
                '<span style="padding:4px 12px;border-radius:6px;'
                'border:1px solid #ef4444;background:#2d0a0a;'
                'color:#f87171;font-size:12px;font-family:monospace;margin:3px;'
                'display:inline-block;">&#9888; {} &nbsp;'
                '<span style="font-size:10px;opacity:0.7;">'
                '{} CVE{}</span></span>'.format(
                    esc(v), num_cves, "s" if num_cves != 1 else ""
                )
            )
        return (
            '<span style="padding:4px 12px;border-radius:6px;'
            'border:1px solid #334155;background:#0f172a;'
            'color:#94a3b8;font-size:12px;font-family:monospace;margin:3px;'
            'display:inline-block;">{}</span>'.format(esc(v))
        )

    # ── Tab 1: Conflicts ───────────────────────────────────────────────────────
    conflict_html = ""
    if not conflict_issues:
        conflict_html = (
            '<div style="text-align:center;padding:80px 40px;color:#4ade80;">'
            '<div style="font-size:56px;">&#10003;</div>'
            '<div style="font-size:20px;font-weight:700;margin-top:16px;">'
            'No version conflicts detected</div></div>'
        )
    else:
        for issue in conflict_issues:
            e       = issue.entry
            col     = SEV.get(issue.severity, ("#94a3b8", "#1e293b"))[0]
            chips   = "".join(
                version_chip(v, e.recommended_version, e.version_vuln_map)
                for v in e.all_versions
            )
            cve_rows = ""
            for v in e.all_versions:
                result = e.version_vuln_map.get(v)
                if result and result.vulnerabilities:
                    for vuln in result.vulnerabilities:
                        cve_rows += (
                            '<tr style="border-bottom:1px solid #1e293b;">'
                            '<td style="padding:10px 14px;font-family:monospace;'
                            'font-size:12px;color:#94a3b8;">{}</td>'
                            '<td style="padding:10px 14px;font-family:monospace;'
                            'font-size:12px;color:#e2e8f0;">{}</td>'
                            '<td style="padding:10px 14px;">{}</td>'
                            '<td style="padding:10px 14px;">{}</td>'
                            '<td style="padding:10px 14px;font-size:12px;'
                            'color:#cbd5e1;">{}</td>'
                            '<td style="padding:10px 14px;font-size:12px;'
                            'color:#4ade80;">{}</td>'
                            '</tr>'.format(
                                esc(v),
                                esc(vuln.cve_id),
                                sev_badge(vuln.severity),
                                cvss_bar(vuln.cvss),
                                esc(vuln.title[:55]),
                                esc(", ".join(vuln.fixed_in) if vuln.fixed_in else "—"),
                            )
                        )

            cve_table = ""
            if cve_rows:
                cve_table = (
                    '<div style="margin-top:20px;border-radius:8px;overflow:hidden;'
                    'border:1px solid #1e293b;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<thead><tr style="background:#0a0f1a;">'
                    + "".join(
                        '<th style="padding:10px 14px;text-align:left;font-size:10px;'
                        'color:#475569;font-weight:700;letter-spacing:0.1em;">{}</th>'.format(h)
                        for h in ["VERSION", "CVE ID", "SEVERITY", "CVSS", "TITLE", "FIXED IN"]
                    )
                    + '</tr></thead><tbody style="background:#0d1117;">'
                    + cve_rows
                    + '</tbody></table></div>'
                )

            sources_html = ""
            if e.sources:
                pills = " ".join(
                    '<code style="background:#0f172a;border:1px solid #1e293b;'
                    'padding:2px 8px;border-radius:4px;font-size:11px;color:#64748b;">'
                    '{}</code>'.format(esc(s)) for s in e.sources
                )
                sources_html = (
                    '<div style="margin-top:12px;font-size:12px;color:#475569;">'
                    'Introduced by: {}</div>'.format(pills)
                )

            conflict_html += (
                '<div style="background:#0d1117;border:1px solid {};'
                'border-radius:12px;margin-bottom:16px;overflow:hidden;">'
                '<div style="padding:20px 24px;">'
                '<div style="display:flex;align-items:flex-start;'
                'justify-content:space-between;gap:16px;flex-wrap:wrap;">'
                '<div>'
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                '{}<span style="font-size:15px;font-weight:700;font-family:monospace;'
                'color:#f1f5f9;">{}</span></div>'
                '<div>{}</div>{}'
                '</div>'
                '<div style="background:#0a0f1a;border:1px solid #1e3a5f;'
                'border-radius:8px;padding:14px 18px;min-width:220px;flex-shrink:0;">'
                '<div style="font-size:10px;font-weight:800;color:#3b82f6;'
                'letter-spacing:0.1em;margin-bottom:8px;">SNYK RECOMMENDATION</div>'
                '<div style="font-family:monospace;font-size:14px;color:#4ade80;'
                'font-weight:700;margin-bottom:6px;">{}</div>'
                '<div style="font-size:12px;color:#64748b;">{}</div>'
                '</div></div>{}</div></div>'
                .format(
                    col,
                    sev_badge(issue.severity),
                    esc(e.ga),
                    chips,
                    sources_html,
                    esc(e.recommended_version or "unknown"),
                    esc(e.recommendation_reason),
                    cve_table,
                )
            )

    # ── Tab 2: Vulnerabilities ─────────────────────────────────────────────────
    vuln_html = ""
    if not vulnerable:
        vuln_html = (
            '<div style="text-align:center;padding:80px 40px;color:#4ade80;">'
            '<div style="font-size:56px;">&#128737;</div>'
            '<div style="font-size:20px;font-weight:700;margin-top:16px;">'
            'All dependencies are clean</div></div>'
        )
    else:
        order_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for dep in vulnerable:
            worst   = sorted(
                dep.vulnerabilities,
                key=lambda v: order_map.get(v.severity, 9)
            )[0]
            col     = SEV.get(worst.severity, ("#94a3b8", "#1e293b"))[0]
            vuln_rows = ""
            for vuln in dep.vulnerabilities:
                vuln_rows += (
                    '<tr style="border-bottom:1px solid #1e293b;">'
                    '<td style="padding:10px 14px;font-family:monospace;'
                    'font-size:12px;color:#94a3b8;">{}</td>'
                    '<td style="padding:10px 14px;">{}</td>'
                    '<td style="padding:10px 14px;">{}</td>'
                    '<td style="padding:10px 14px;font-size:12px;color:#cbd5e1;">{}</td>'
                    '<td style="padding:10px 14px;font-size:12px;color:#4ade80;'
                    'font-weight:600;">{}</td>'
                    '</tr>'.format(
                        esc(vuln.cve_id),
                        sev_badge(vuln.severity),
                        cvss_bar(vuln.cvss),
                        esc(vuln.title[:65]),
                        esc(", ".join(vuln.fixed_in) if vuln.fixed_in else "No fix available"),
                    )
                )

            safe_html = ""
            if dep.safe_version:
                safe_html = (
                    '<div style="margin-top:16px;display:inline-flex;'
                    'align-items:center;gap:10px;background:#052e16;'
                    'border:1px solid #166534;border-radius:8px;padding:10px 16px;">'
                    '<span style="font-size:12px;color:#86efac;">Upgrade to</span>'
                    '<code style="font-size:13px;font-weight:700;color:#4ade80;">{}</code>'
                    '<span style="font-size:11px;color:#4ade80;">'
                    '&#10140; fixes all known CVEs</span>'
                    '</div>'.format(esc(dep.safe_version))
                )

            vuln_html += (
                '<div style="background:#0d1117;border:1px solid {};'
                'border-radius:12px;margin-bottom:16px;overflow:hidden;">'
                '<div style="padding:20px 24px;">'
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">'
                '{}'
                '<span style="font-size:14px;font-weight:700;font-family:monospace;'
                'color:#f1f5f9;display:inline-block;min-width:100px;">{}</span>'
                '<span style="font-size:12px;color:#475569;">{} CVE{}</span>'
                '</div>'
                '<div style="border-radius:8px;overflow:hidden;border:1px solid #1e293b;">'
                '<table style="width:100%;border-collapse:collapse;">'
                '<thead><tr style="background:#0a0f1a;">'
                + "".join(
                    '<th style="padding:10px 14px;text-align:left;font-size:10px;'
                    'color:#475569;font-weight:700;letter-spacing:0.1em;">{}</th>'.format(h)
                    for h in ["CVE ID", "SEVERITY", "CVSS", "TITLE", "FIXED IN"]
                )
                + '</tr></thead><tbody style="background:#0d1117;">'
                + vuln_rows
                + '</tbody></table></div>'
                + safe_html
                + '</div></div>'
            ).format(
                col,
                sev_badge(worst.severity),
                esc(dep.gav),
                len(dep.vulnerabilities),
                "s" if len(dep.vulnerabilities) != 1 else "",
            )

    clean_html = ""
    if clean:
        pills = "".join(
            '<span style="display:inline-block;background:#0a1a0a;'
            'border:1px solid #14532d;color:#4ade80;border-radius:6px;'
            'padding:4px 10px;font-size:11px;font-family:monospace;margin:3px;">'
            '&#10003; {}</span>'.format(esc(r.gav)) for r in clean
        )
        clean_html = (
            '<div style="margin-top:32px;">'
            '<div style="font-size:13px;font-weight:700;color:#4ade80;'
            'letter-spacing:0.05em;margin-bottom:12px;">'
            'CLEAN DEPENDENCIES ({})</div>'
            '<div>{}</div></div>'.format(len(clean), pills)
        )

    # ── Tab 3: Unused ──────────────────────────────────────────────────────────
    unused_html = ""
    if not unused_results:
        unused_html = (
            '<div style="text-align:center;padding:80px 40px;color:#4ade80;">'
            '<div style="font-size:56px;">&#10003;</div>'
            '<div style="font-size:20px;font-weight:700;margin-top:16px;">'
            'No unused dependencies found</div></div>'
        )
    else:
        unused_data_for_js = {}
        cards_html = ""
        for gradle_path, results in unused_results.items():
            rows = ""
            unused_data_for_js[gradle_path] = []
            for result in results:
                dep_id = "dep-{}-{}".format(
                    gradle_path.replace("/", "-").replace(".", "-"),
                    result.declaration.artifact,
                )
                tag_html = (
                    '<span style="padding:2px 8px;border-radius:4px;font-size:10px;'
                    'font-weight:800;background:#2d0a0a;color:#f87171;'
                    'border:1px solid #ef4444;">UNUSED</span>'
                    if result.is_unused else
                    '<span style="padding:2px 8px;border-radius:4px;font-size:10px;'
                    'font-weight:800;background:#1a2d0a;color:#86efac;'
                    'border:1px solid #22c55e;">TEST-ONLY</span>'
                )
                conf_color = (
                    "#4ade80" if result.confidence == "HIGH" else
                    "#fbbf24" if result.confidence == "MEDIUM" else
                    "#94a3b8"
                )
                action_hint = (
                    "Will be removed" if result.is_unused
                    else "Move to testImplementation"
                )
                unused_data_for_js[gradle_path].append({
                    "dep_id":        dep_id,
                    "gav":           result.declaration.gav,
                    "artifact":      result.declaration.artifact,
                    "configuration": result.declaration.configuration,
                    "line_number":   result.declaration.line_number,
                    "raw_line":      result.declaration.raw_line,
                    "is_unused":     result.is_unused,
                    "is_test_only":  result.is_test_only,
                    "reason":        result.reason,
                })
                rows += (
                    '<tr style="border-bottom:1px solid #1e293b;">'
                    '<td style="padding:12px 14px;width:40px;">'
                    '<input type="checkbox" id="{dep_id}" value="{dep_id}"'
                    ' data-gradle="{gradle}" data-artifact="{artifact}"'
                    ' data-line="{line}" data-action="{action}"'
                    ' style="width:16px;height:16px;cursor:pointer;"'
                    ' onchange="updateSelection()"></td>'
                    '<td style="padding:12px 14px;">'
                    '<code style="font-size:13px;color:#e2e8f0;">{gav}</code></td>'
                    '<td style="padding:12px 14px;">'
                    '<code style="font-size:12px;color:#64748b;">{config}</code></td>'
                    '<td style="padding:12px 14px;">{tag}</td>'
                    '<td style="padding:12px 14px;font-size:12px;color:#94a3b8;">{reason}</td>'
                    '<td style="padding:12px 14px;font-size:11px;color:{conf_color};">{conf}</td>'
                    '<td style="padding:12px 14px;font-size:11px;color:#475569;">{action_hint}</td>'
                    '</tr>'.format(
                        dep_id=dep_id,
                        gradle=esc(gradle_path),
                        artifact=esc(result.declaration.artifact),
                        line=result.declaration.line_number,
                        action="remove" if result.is_unused else "move",
                        gav=esc(result.declaration.gav),
                        config=esc(result.declaration.configuration),
                        tag=tag_html,
                        reason=esc(result.reason),
                        conf_color=conf_color,
                        conf=result.confidence,
                        action_hint=action_hint,
                    )
                )

            gradle_id = gradle_path.replace("/", "-").replace(".", "-")
            cards_html += (
                '<div style="background:#0d1117;border:1px solid #1e293b;'
                'border-radius:12px;margin-bottom:20px;overflow:hidden;">'
                '<div style="padding:14px 20px;border-bottom:1px solid #1e293b;'
                'display:flex;align-items:center;justify-content:space-between;">'
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<span style="font-size:14px;">&#128196;</span>'
                '<code style="font-size:13px;font-weight:700;color:#e2e8f0;">{gradle_path}</code>'
                '</div>'
                '<span style="font-size:12px;color:#475569;">{count} issue(s)</span>'
                '</div>'
                '<div style="overflow-x:auto;">'
                '<table style="width:100%;border-collapse:collapse;">'
                '<thead><tr style="background:#0a0f1a;">'
                '<th style="padding:10px 14px;width:40px;">'
                '<input type="checkbox" onchange="toggleFile(this,\'{gradle_id}\')"'
                ' style="width:16px;height:16px;cursor:pointer;"></th>'
                + "".join(
                    '<th style="padding:10px 14px;text-align:left;font-size:10px;'
                    'color:#475569;font-weight:700;letter-spacing:0.1em;">{}</th>'.format(h)
                    for h in ["DEPENDENCY", "CONFIG", "STATUS", "REASON", "CONFIDENCE", "ACTION"]
                )
                + '</tr></thead>'
                '<tbody style="background:#0d1117;">{rows}</tbody>'
                '</table></div></div>'
            ).format(
                gradle_path=esc(gradle_path),
                count=len(results),
                gradle_id=gradle_id,
                rows=rows,
            )

        pr_panel = (
            '<div style="position:sticky;bottom:0;background:#060a12;'
            'border-top:1px solid #1e293b;padding:16px 0;margin-top:24px;">'
            '<div style="max-width:1280px;margin:0 auto;padding:0 40px;">'
            '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
            '<div style="font-size:13px;color:#64748b;" id="selection-count">'
            '0 dependencies selected</div>'
            '<div style="display:flex;align-items:center;gap:8px;flex:1;min-width:240px;">'
            '<label style="font-size:12px;color:#64748b;white-space:nowrap;">PR Branch:</label>'
            '<input type="text" id="pr-branch-input" value="dependency-refractor/remove-unused"'
            ' style="flex:1;background:#0d1117;border:1px solid #334155;border-radius:6px;'
            'padding:8px 12px;color:#e2e8f0;font-family:monospace;font-size:12px;outline:none;">'
            '</div>'
            '<button onclick="previewDiff()" style="padding:10px 20px;background:#1e3a5f;'
            'border:1px solid #3b82f6;border-radius:8px;color:#93c5fd;'
            'font-size:13px;font-weight:600;cursor:pointer;">&#128269; Preview</button>'
            '<button onclick="submitPR()" id="submit-pr-btn" disabled'
            ' style="padding:10px 24px;background:#166534;border:1px solid #22c55e;'
            'border-radius:8px;color:#4ade80;font-size:13px;font-weight:700;'
            'cursor:not-allowed;opacity:0.5;">&#10145; Submit PR</button>'
            '</div></div></div>'
        )

        diff_modal = (
            '<div id="diff-modal" style="display:none;position:fixed;inset:0;'
            'background:rgba(0,0,0,0.85);z-index:9999;'
            'align-items:center;justify-content:center;">'
            '<div style="background:#0d1117;border:1px solid #334155;'
            'border-radius:16px;width:90%;max-width:900px;max-height:85vh;'
            'display:flex;flex-direction:column;overflow:hidden;">'
            '<div style="padding:20px 24px;border-bottom:1px solid #1e293b;'
            'display:flex;align-items:center;justify-content:space-between;">'
            '<div style="font-size:15px;font-weight:700;color:#e2e8f0;">'
            '&#128269; Diff Preview</div>'
            '<button onclick="closeDiff()" style="background:none;border:none;'
            'color:#64748b;font-size:20px;cursor:pointer;">&#10005;</button>'
            '</div>'
            '<div style="padding:20px 24px;overflow-y:auto;flex:1;">'
            '<pre id="diff-content" style="font-family:monospace;font-size:12px;'
            'line-height:1.6;color:#94a3b8;white-space:pre-wrap;">'
            'Select dependencies and click Preview</pre>'
            '</div>'
            '<div style="padding:16px 24px;border-top:1px solid #1e293b;'
            'display:flex;justify-content:flex-end;gap:12px;">'
            '<button onclick="closeDiff()" style="padding:10px 20px;'
            'background:#0d1117;border:1px solid #334155;border-radius:8px;'
            'color:#94a3b8;font-size:13px;cursor:pointer;">Cancel</button>'
            '<button onclick="confirmSubmit()" style="padding:10px 24px;'
            'background:#166534;border:1px solid #22c55e;border-radius:8px;'
            'color:#4ade80;font-size:13px;font-weight:700;cursor:pointer;">'
            '&#10145; Confirm &amp; Submit PR</button>'
            '</div></div></div>'
        )

        unused_html = (
            '<div style="display:flex;justify-content:space-between;'
            'align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;">'
            '<div>'
            '<div style="font-size:14px;font-weight:700;color:#64748b;'
            'letter-spacing:0.1em;text-transform:uppercase;">UNUSED DEPENDENCIES</div>'
            '<div style="font-size:12px;color:#475569;margin-top:4px;">'
            '{} unused &middot; {} test-only</div>'
            '</div></div>'
            .format(total_unused, total_test_only)
            + cards_html + pr_panel + diff_modal
            + '<script>var UNUSED_DATA = {};</script>'.format(
                json.dumps(unused_data_for_js)
            )
        )

    # ── Stat boxes ─────────────────────────────────────────────────────────────
    def stat_box(icon, value, label, color):
        return (
            '<div style="background:#0d1117;border:1px solid #1e293b;'
            'border-radius:12px;padding:20px 28px;text-align:center;'
            'flex:1;min-width:120px;">'
            '<div style="font-size:24px;margin-bottom:4px;">{}</div>'
            '<div style="font-size:30px;font-weight:800;color:{};">{}</div>'
            '<div style="font-size:11px;color:#475569;font-weight:700;'
            'letter-spacing:0.1em;margin-top:4px;">{}</div>'
            '</div>'.format(icon, color, value, label)
        )

    stats = (
        stat_box("&#128196;", total_deps,   "TOTAL DEPS",  "#e2e8f0") +
        stat_box("&#9889;",   total_conf,   "CONFLICTS",   "#ff8c00" if total_conf  else "#4ade80") +
        stat_box("&#9888;",   total_vuln,   "VULNERABLE",  "#ff4444" if total_vuln  else "#4ade80") +
        stat_box("&#128465;", total_unused + total_test_only, "UNUSED", "#fbbf24" if (total_unused + total_test_only) else "#4ade80") +
        stat_box("&#10003;",  total_clean,  "CLEAN",       "#4ade80")
    )

    # ── Full HTML ───────────────────────────────────────────────────────────────
    html = (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>dependency_refractor &mdash; {service}</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700'
        '&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">'
        '<style>'
        ':root{{--bg:#060a12;--surface:#0d1117;--border:#1e293b;'
        '--text:#e2e8f0;--muted:#475569;--accent:#3b82f6;}}'
        '*{{box-sizing:border-box;margin:0;padding:0;}}'
        'body{{font-family:"DM Sans",sans-serif;background:var(--bg);'
        'color:var(--text);min-height:100vh;}}'
        'code{{font-family:"Space Mono",monospace;}}'
        '#loading-overlay{{position:fixed;inset:0;z-index:9999;'
        'background:var(--bg);display:flex;flex-direction:column;'
        'align-items:center;justify-content:center;gap:24px;'
        'transition:opacity 0.6s ease,visibility 0.6s ease;}}'
        '#loading-overlay.hidden{{opacity:0;visibility:hidden;}}'
        '.loader-ring{{width:64px;height:64px;border:3px solid var(--border);'
        'border-top-color:var(--accent);border-radius:50%;'
        'animation:spin 1s linear infinite;}}'
        '@keyframes spin{{to{{transform:rotate(360deg)}}}}'
        '.loader-dots{{display:flex;gap:8px;}}'
        '.loader-dots span{{width:6px;height:6px;background:var(--accent);'
        'border-radius:50%;animation:pd 1.2s ease-in-out infinite;}}'
        '.loader-dots span:nth-child(2){{animation-delay:0.2s;}}'
        '.loader-dots span:nth-child(3){{animation-delay:0.4s;}}'
        '@keyframes pd{{0%,80%,100%{{transform:scale(0.6);opacity:0.4}}'
        '40%{{transform:scale(1);opacity:1}}}}'
        '.loader-text{{font-family:"Space Mono",monospace;font-size:13px;'
        'color:var(--muted);letter-spacing:0.1em;}}'
        '.loader-status{{font-size:12px;color:var(--accent);'
        'font-family:"Space Mono",monospace;min-height:20px;}}'
        '.header{{background:linear-gradient(180deg,#080c16 0%,var(--bg) 100%);'
        'border-bottom:1px solid var(--border);padding:28px 40px;'
        'position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}}'
        '.header-inner{{max-width:1280px;margin:0 auto;display:flex;'
        'align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;}}'
        '.brand{{display:flex;align-items:center;gap:12px;}}'
        '.brand-icon{{width:36px;height:36px;background:linear-gradient(135deg,#1d4ed8,#7c3aed);'
        'border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;}}'
        '.brand-name{{font-family:"Space Mono",monospace;font-size:15px;font-weight:700;}}'
        '.brand-sub{{font-size:11px;color:var(--muted);letter-spacing:0.05em;}}'
        '.header-meta{{display:flex;gap:8px;flex-wrap:wrap;}}'
        '.meta-chip{{background:var(--surface);border:1px solid var(--border);'
        'border-radius:8px;padding:8px 14px;}}'
        '.meta-chip-label{{font-size:9px;color:var(--muted);font-weight:700;'
        'letter-spacing:0.12em;text-transform:uppercase;}}'
        '.meta-chip-value{{font-size:13px;font-weight:600;font-family:"Space Mono",monospace;'
        'margin-top:2px;}}'
        '.stats-bar{{border-bottom:1px solid var(--border);padding:20px 40px;'
        'background:var(--bg);}}'
        '.stats-inner{{max-width:1280px;margin:0 auto;display:flex;gap:12px;flex-wrap:wrap;}}'
        '.tabs-bar{{border-bottom:1px solid var(--border);padding:0 40px;'
        'background:var(--bg);position:sticky;top:85px;z-index:99;}}'
        '.tabs-inner{{max-width:1280px;margin:0 auto;display:flex;}}'
        '.tab-btn{{padding:16px 24px;cursor:pointer;font-size:13px;font-weight:600;'
        'color:var(--muted);border:none;background:none;'
        'border-bottom:2px solid transparent;margin-bottom:-1px;'
        'transition:all 0.2s;font-family:"DM Sans",sans-serif;}}'
        '.tab-btn:hover{{color:var(--text)}}'
        '.tab-btn.active{{color:var(--accent);border-bottom-color:var(--accent)}}'
        '.tab-count{{display:inline-flex;align-items:center;justify-content:center;'
        'min-width:20px;height:20px;border-radius:10px;font-size:10px;'
        'font-weight:800;padding:0 6px;margin-left:6px;}}'
        '.tab-count.warn{{background:#2d1800;color:#fb923c}}'
        '.tab-count.danger{{background:#2d0a0a;color:#f87171}}'
        '.tab-count.ok{{background:#052e16;color:#4ade80}}'
        '.tab-count.info{{background:#1e3a5f;color:#93c5fd}}'
        '.content{{max-width:1280px;margin:0 auto;padding:32px 40px;}}'
        '.tab-panel{{display:none;}}'
        '.tab-panel.active{{display:block;}}'
        '.fade-in{{animation:fi 0.4s ease forwards;opacity:0;}}'
        '@keyframes fi{{from{{opacity:0;transform:translateY(8px)}}'
        'to{{opacity:1;transform:translateY(0)}}}}'
        '</style></head><body>'

        # Loading overlay
        '<div id="loading-overlay">'
        '<div class="brand" style="margin-bottom:8px;">'
        '<div class="brand-icon">&#128270;</div>'
        '<div><div class="brand-name">dependency_refractor</div>'
        '<div class="brand-sub">SECURITY ANALYSIS</div></div></div>'
        '<div class="loader-ring"></div>'
        '<div class="loader-dots"><span></span><span></span><span></span></div>'
        '<div class="loader-text">Preparing report&hellip;</div>'
        '<div class="loader-status" id="loader-status">Loading results</div>'
        '</div>'

        # Header
        '<div class="header"><div class="header-inner">'
        '<div class="brand">'
        '<div class="brand-icon">&#128270;</div>'
        '<div><div class="brand-name">dependency_refractor</div>'
        '<div class="brand-sub">SECURITY ANALYSIS PLATFORM</div></div>'
        '</div>'
        '<div class="header-meta">'
        '<div class="meta-chip"><div class="meta-chip-label">Service</div>'
        '<div class="meta-chip-value">{service}</div></div>'
        '<div class="meta-chip"><div class="meta-chip-label">Branch</div>'
        '<div class="meta-chip-value">{branch}</div></div>'
        '<div class="meta-chip"><div class="meta-chip-label">Scan Engine</div>'
        '<div class="meta-chip-value">Snyk</div></div>'
        '</div>'
        '<div style="font-size:11px;color:#475569;font-family:\'Space Mono\',monospace;">'
        'Scanned {now}</div>'
        '</div></div>'

        # Stats
        '<div class="stats-bar"><div class="stats-inner">{stats}</div></div>'

        # Tabs
        '<div class="tabs-bar"><div class="tabs-inner">'
        '<button class="tab-btn active" onclick="switchTab(\'conflicts\',this)">'
        '&#9889; Conflict Analysis'
        '<span class="tab-count {conf_cls}">{conf_count}</span></button>'
        '<button class="tab-btn" onclick="switchTab(\'vulns\',this)">'
        '&#9888;&#65039; Vulnerability Scan'
        '<span class="tab-count {vuln_cls}">{vuln_count}</span></button>'
        '<button class="tab-btn" onclick="switchTab(\'unused\',this)">'
        '&#128465; Unused Dependencies'
        '<span class="tab-count {unused_cls}">{unused_count}</span></button>'
        '</div></div>'

        # Content
        '<div class="content">'
        '<div id="tab-conflicts" class="tab-panel active fade-in">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'margin-bottom:20px;"><div style="font-size:14px;font-weight:700;'
        'color:#64748b;letter-spacing:0.1em;text-transform:uppercase;">'
        'VERSION CONFLICTS</div>'
        '<div style="font-size:12px;color:#475569;">'
        '{conf_count} conflict{conf_plural} &middot; each version checked against Snyk'
        '</div></div>'
        '{conflict_html}</div>'

        '<div id="tab-vulns" class="tab-panel fade-in">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'margin-bottom:20px;"><div style="font-size:14px;font-weight:700;'
        'color:#64748b;letter-spacing:0.1em;text-transform:uppercase;">'
        'VULNERABLE DEPENDENCIES</div>'
        '<div style="font-size:12px;color:#475569;">'
        '{vuln_count} vulnerable &middot; {clean_count} clean'
        '</div></div>'
        '{vuln_html}{clean_html}</div>'

        '<div id="tab-unused" class="tab-panel fade-in">'
        '{unused_html}</div>'
        '</div>'

        '<div style="text-align:center;padding:32px;color:#1e293b;font-size:11px;'
        'font-family:\'Space Mono\',monospace;border-top:1px solid #0d1117;">'
        'dependency_refractor &mdash; {service} &mdash; {branch} &mdash; {now}'
        '</div>'

        '<script>'
        'var statuses=["Parsing dependency tree...","Running conflict analysis...",'
        '"Querying Snyk for vulnerabilities...","Detecting unused dependencies...",'
        '"Building report...","Done."];'
        'var si=0,statusEl=document.getElementById("loader-status");'
        'var iv=setInterval(function(){si++;if(si<statuses.length){'
        'statusEl.style.opacity="0";'
        'setTimeout(function(){statusEl.textContent=statuses[si];'
        'statusEl.style.opacity="1";},200);}else{clearInterval(iv);}},700);'
        'setTimeout(function(){'
        'document.getElementById("loading-overlay").classList.add("hidden");},4000);'
        'function switchTab(name,el){'
        'document.querySelectorAll(".tab-panel").forEach(function(p){'
        'p.classList.remove("active");});'
        'document.querySelectorAll(".tab-btn").forEach(function(b){'
        'b.classList.remove("active");});'
        'var panel=document.getElementById("tab-"+name);'
        'panel.classList.add("active");'
        'panel.classList.remove("fade-in");void panel.offsetWidth;'
        'panel.classList.add("fade-in");el.classList.add("active");}'
        'function updateSelection(){'
        'var checked=document.querySelectorAll("#tab-unused input[type=checkbox][id^=dep-]:checked");'
        'document.getElementById("selection-count").textContent='
        'checked.length+" dependenc"+(checked.length===1?"y":"ies")+" selected";'
        'var btn=document.getElementById("submit-pr-btn");'
        'btn.disabled=checked.length===0;'
        'btn.style.opacity=checked.length===0?"0.5":"1";'
        'btn.style.cursor=checked.length===0?"not-allowed":"pointer";}'
        'function toggleFile(master,gradleId){'
        'document.querySelectorAll("#tab-unused input[data-gradle]").forEach(function(cb){'
        'var rg=cb.getAttribute("data-gradle").replace(/\\//g,"-").replace(/\\./g,"-");'
        'if(rg===gradleId)cb.checked=master.checked;});updateSelection();}'
        'function getSelections(){'
        'var checked=document.querySelectorAll("#tab-unused input[type=checkbox][id^=dep-]:checked");'
        'var result={};'
        'checked.forEach(function(cb){'
        'var g=cb.getAttribute("data-gradle");'
        'if(!result[g])result[g]=[];'
        'result[g].push({artifact:cb.getAttribute("data-artifact"),'
        'line:parseInt(cb.getAttribute("data-line")),'
        'action:cb.getAttribute("data-action")});});return result;}'
        'function previewDiff(){'
        'var sel=getSelections();'
        'if(!Object.keys(sel).length){alert("Select at least one dependency.");return;}'
        'var txt="";'
        'for(var gp in sel){'
        'var deps=UNUSED_DATA[gp]||[];var chosen=sel[gp];'
        'var toRemove=chosen.filter(function(s){return s.action==="remove";}).map(function(s){return s.line;});'
        'var toMove=chosen.filter(function(s){return s.action==="move";}).map(function(s){return s.line;});'
        'txt+="--- a/"+gp+"\\n+++ b/"+gp+"\\n";'
        'deps.forEach(function(dep){'
        'if(toRemove.indexOf(dep.line_number)!==-1){'
        'txt+="\\n@@ line "+dep.line_number+" @@\\n";'
        'txt+="-  "+dep.raw_line.trim()+"\\n";}' 
        'else if(toMove.indexOf(dep.line_number)!==-1){'
        'var nl=dep.raw_line.replace(dep.configuration,"testImplementation");'
        'txt+="\\n@@ line "+dep.line_number+" @@\\n";'
        'txt+="-  "+dep.raw_line.trim()+"\\n";'
        'txt+="+  "+nl.trim()+"\\n";}});txt+="\\n";}'
        'document.getElementById("diff-content").textContent=txt;'
        'document.getElementById("diff-modal").style.display="flex";}'
        'function closeDiff(){document.getElementById("diff-modal").style.display="none";}'
        'function confirmSubmit(){closeDiff();submitPR();}'
        'function submitPR(){'
        'var sel=getSelections();'
        'var branch=document.getElementById("pr-branch-input").value.trim();'
        'if(!branch){alert("Enter a PR branch name.");return;}'
        'if(!Object.keys(sel).length){alert("Select at least one dependency.");return;}'
        'document.getElementById("pr-payload").value=JSON.stringify({selections:sel,pr_branch:branch});'
        'alert("Selection captured!\\nRun the PR submission step in the app to submit.\\nBranch: "+branch);}'
        '</script>'
        '<input type="hidden" id="pr-payload" value="">'
        '</body></html>'
    ).format(
        service=esc(service_name),
        branch=esc(branch_name),
        now=now,
        stats=stats,
        conf_cls="warn" if total_conf > 0 else "ok",
        conf_count=total_conf,
        conf_plural="s" if total_conf != 1 else "",
        vuln_cls="danger" if total_vuln > 0 else "ok",
        vuln_count=total_vuln,
        clean_count=total_clean,
        unused_cls="info" if (total_unused + total_test_only) > 0 else "ok",
        unused_count=total_unused + total_test_only,
        conflict_html=conflict_html,
        vuln_html=vuln_html,
        clean_html=clean_html,
        unused_html=unused_html,
    )

    return html