import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from backend.core.fix_delta_extractor import FixDelta
from backend.core.github_client import GitHubClient

logger = logging.getLogger("dependency_refractor.propagation")


@dataclass
class RepoFixSummary:
    """Summary of applicable fixes for one target repo."""
    repo_url:          str
    repo_name:         str
    branch:            str
    applicable_fixes:  List[FixDelta]       = field(default_factory=list)
    already_safe:      List[FixDelta]       = field(default_factory=list)
    not_present:       List[FixDelta]       = field(default_factory=list)
    gradle_files:      List[str]            = field(default_factory=list)
    error:             Optional[str]        = None
    pr_url:            Optional[str]        = None
    status:            str                  = "pending"  # pending | submitted | error | skipped

    @property
    def has_fixes(self):
        # type: () -> bool
        return len(self.applicable_fixes) > 0


@dataclass
class PropagationResult:
    """Full propagation result across all target repos."""
    fix_deltas:    List[FixDelta]
    repo_summaries: List[RepoFixSummary]

    @property
    def total_repos(self):
        # type: () -> int
        return len(self.repo_summaries)

    @property
    def repos_with_fixes(self):
        # type: () -> int
        return sum(1 for r in self.repo_summaries if r.has_fixes)

    @property
    def repos_already_safe(self):
        # type: () -> int
        return sum(1 for r in self.repo_summaries if not r.has_fixes and not r.error)

    @property
    def repos_with_errors(self):
        # type: () -> int
        return sum(1 for r in self.repo_summaries if r.error)


class PropagationEngine:
    """
    Scans target repos and computes which fix deltas apply to each.

    For each target repo:
      1. Fetch all build.gradle files
      2. For each FixDelta — check if that dep exists and at what version
      3. Classify as: applicable | already_safe | not_present
    """

    GRADLE_DEP_RE = re.compile(
        r"(?P<config>implementation|api|compileOnly|runtimeOnly|"
        r"testImplementation|annotationProcessor)\s+"
        r"['\"](?P<group>[\w.\-]+):(?P<artifact>[\w.\-]+)"
        r":(?P<version>[\w.\-+${}]+)['\"]"
    )

    def __init__(self, github_pat, proxy_url="",
                 ssl_verify=True, timeout=60):
        # type: (str, str, object, int) -> None
        self.github_pat  = github_pat
        self.proxy_url   = proxy_url
        self.ssl_verify  = ssl_verify
        self.timeout     = timeout

    def _make_github_client(self, repo_name):
        # type: (str) -> GitHubClient
        return GitHubClient(
            pat=self.github_pat,
            repo=repo_name,
            proxy_url=self.proxy_url,
            ssl_verify=self.ssl_verify,
            timeout=self.timeout,
        )

    def scan_repos(self, repo_urls, branch, fix_deltas):
        # type: (List[str], str, List[FixDelta]) -> PropagationResult
        """
        Scan all target repos and compute applicable fixes.
        Returns PropagationResult with summary per repo.
        """
        summaries = []

        for repo_url in repo_urls:
            repo_name = repo_url.replace(
                "https://github.com/", ""
            ).rstrip("/")

            logger.info("Scanning repo: {}".format(repo_name))
            summary = self._scan_single_repo(
                repo_url, repo_name, branch, fix_deltas
            )
            summaries.append(summary)
            logger.info("  Applicable: {} | Already safe: {} | Not present: {}".format(
                len(summary.applicable_fixes),
                len(summary.already_safe),
                len(summary.not_present),
            ))

        return PropagationResult(
            fix_deltas=fix_deltas,
            repo_summaries=summaries,
        )

    def _scan_single_repo(self, repo_url, repo_name,
                           branch, fix_deltas):
        # type: (str, str, str, List[FixDelta]) -> RepoFixSummary
        summary = RepoFixSummary(
            repo_url=repo_url,
            repo_name=repo_name,
            branch=branch,
        )

        try:
            github = self._make_github_client(repo_name)
            tree   = github.get_tree(branch)

            gradle_files = [
                f["path"] for f in tree
                if f["path"].endswith("build.gradle")
                and "buildSrc" not in f["path"]
            ]
            summary.gradle_files = gradle_files

            if not gradle_files:
                summary.error = "No build.gradle files found on branch '{}'".format(branch)
                return summary

            # Collect all declared deps across all gradle files
            declared = {}   # type: Dict[str, Dict]  # ga -> {version, config, file, line}
            for gradle_path in gradle_files:
                try:
                    content = github.get_file_content(gradle_path, branch)
                    for line_num, line in enumerate(content.splitlines(), 1):
                        m = self.GRADLE_DEP_RE.search(line)
                        if not m:
                            continue
                        ga = "{}:{}".format(
                            m.group("group"), m.group("artifact")
                        )
                        if ga not in declared:
                            declared[ga] = {
                                "version":     m.group("version"),
                                "config":      m.group("config"),
                                "gradle_file": gradle_path,
                                "line_number": line_num,
                                "raw_line":    line,
                            }
                except Exception as e:
                    logger.warning("Could not read {} in {}: {}".format(
                        gradle_path, repo_name, e
                    ))

            # Classify each fix delta
            for delta in fix_deltas:
                if delta.ga not in declared:
                    summary.not_present.append(delta)
                    continue

                current_version = declared[delta.ga]["version"]

                if current_version == delta.to_version:
                    summary.already_safe.append(delta)
                    continue

                # Applicable — attach the current version info
                applicable_delta = FixDelta(
                    ga=delta.ga,
                    from_version=current_version,   # actual version in THIS repo
                    to_version=delta.to_version,
                    reason=delta.reason,
                    cve_ids=delta.cve_ids,
                )
                applicable_delta.gradle_file = declared[delta.ga]["gradle_file"]
                applicable_delta.line_number = declared[delta.ga]["line_number"]
                applicable_delta.raw_line    = declared[delta.ga]["raw_line"]
                applicable_delta.config      = declared[delta.ga]["config"]
                summary.applicable_fixes.append(applicable_delta)

        except Exception as e:
            logger.error("Error scanning {}: {}".format(repo_name, e), exc_info=True)
            summary.error = str(e)

        return summary

def submit_pr(self, summary, pr_branch_prefix,
              pr_title=None, pr_description=None):
    # type: (RepoFixSummary, str, str, str) -> str
    import datetime
    date_str  = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    pr_branch = "{}/{}".format(pr_branch_prefix, date_str)

    github = self._make_github_client(summary.repo_name)

    # ── Step 1: Discover actual build.gradle paths from repo tree ──────────
    logger.info("Discovering build.gradle paths in '{}'".format(
        summary.repo_name
    ))
    tree = github.get_tree(summary.branch)
    actual_gradle_paths = [
        f["path"] for f in tree
        if f["path"].endswith("build.gradle")
        and "buildSrc" not in f["path"]
    ]
    logger.info("Found gradle files: {}".format(actual_gradle_paths))

    if not actual_gradle_paths:
        raise RuntimeError(
            "No build.gradle files found in '{}' on branch '{}'".format(
                summary.repo_name, summary.branch
            )
        )

    def resolve_path(incoming_path):
        # type: (str) -> str
        if incoming_path in actual_gradle_paths:
            return incoming_path
        matches = [
            p for p in actual_gradle_paths
            if p.endswith(incoming_path) or p == incoming_path
        ]
        if matches:
            logger.info("Resolved '{}' -> '{}'".format(
                incoming_path, matches[0]
            ))
            return matches[0]
        if actual_gradle_paths:
            logger.warning(
                "Could not resolve '{}' — falling back to '{}'".format(
                    incoming_path, actual_gradle_paths[0]
                )
            )
            return actual_gradle_paths[0]
        raise RuntimeError(
            "Cannot resolve gradle path '{}'".format(incoming_path)
        )

    # ── Step 2: Group fixes by actual resolved gradle file ─────────────────
    fixes_by_file = {}   # type: Dict[str, List]
    for fix in summary.applicable_fixes:
        incoming = getattr(fix, "gradle_file", "") or ""
        if not incoming:
            # No gradle file hint — apply to all gradle files
            # that contain this dependency
            logger.warning(
                "No gradle_file on fix for {} — "
                "will search all gradle files".format(fix.ga)
            )
            for actual_path in actual_gradle_paths:
                if actual_path not in fixes_by_file:
                    fixes_by_file[actual_path] = []
                fixes_by_file[actual_path].append(fix)
        else:
            actual_path = resolve_path(incoming)
            if actual_path not in fixes_by_file:
                fixes_by_file[actual_path] = []
            fixes_by_file[actual_path].append(fix)

    if not fixes_by_file:
        raise RuntimeError("No fixes with valid gradle file paths found")

    logger.info("Fixes by file: {}".format(list(fixes_by_file.keys())))

    # ── Step 3: Get HEAD SHA and create branch ─────────────────────────────
    head_sha = github.get_branch_sha(summary.branch)
    logger.info("HEAD SHA: {}".format(head_sha))

    try:
        github.create_branch(pr_branch, head_sha)
        logger.info("Branch created: {}".format(pr_branch))
    except Exception as e:
        logger.warning(
            "Branch creation failed (may already exist): {}".format(e)
        )

    # ── Step 4: Commit each modified gradle file ───────────────────────────
    for actual_path, fixes in fixes_by_file.items():
        logger.info("Processing '{}' — {} fix(es)".format(
            actual_path, len(fixes)
        ))

        try:
            original = github.get_file_content(actual_path, summary.branch)
            logger.info("Content fetched: {} chars".format(len(original)))
        except Exception as e:
            logger.error("Could not fetch '{}': {}".format(actual_path, e))
            continue

        # Only commit if the file actually contains the dep
        modified = self._apply_fixes(original, fixes)
        if modified == original:
            logger.info("No changes in '{}' — skipping".format(actual_path))
            continue

        try:
            file_sha = github.get_file_sha(actual_path, summary.branch)
            logger.info("File SHA: {}".format(file_sha))
        except Exception as e:
            logger.error("Could not get SHA for '{}': {}".format(actual_path, e))
            continue

        commit_msg = "chore(deps): upgrade {} dep(s) in {}".format(
            len(fixes), actual_path
        )

        try:
            github.commit_file(
                path=actual_path,
                new_content=modified,
                branch=pr_branch,
                message=commit_msg,
                file_sha=file_sha,
            )
            logger.info("Committed: {}".format(actual_path))
        except Exception as e:
            logger.error("Commit failed for '{}': {}".format(actual_path, e))
            continue

    # ── Step 5: Open PR ────────────────────────────────────────────────────
    title = pr_title or "chore(deps): fix vulnerable dependencies"
    body_lines = [
        pr_description or "Automated fix by dependency_refractor.",
        "",
        "---",
        "### Changes",
        "",
    ]
    for fix in summary.applicable_fixes:
        body_lines.append(
            "- `{}` `{}` → `{}` — {}".format(
                fix.ga,
                fix.from_version,
                fix.to_version,
                ", ".join(fix.cve_ids[:3]) if fix.cve_ids else fix.reason,
            )
        )
    body_lines += [
        "",
        "---",
        "_Raised by dependency_refractor_",
    ]

    logger.info("Opening PR '{}' -> '{}'".format(pr_branch, summary.branch))
    try:
        pr_url = github.create_pr(
            title=title,
            body="\n".join(body_lines),
            head_branch=pr_branch,
            base_branch=summary.branch,
        )
        logger.info("PR created: {}".format(pr_url))
        return pr_url
    except Exception as e:
        logger.error("PR creation failed: {}".format(e))
        raise RuntimeError(
            "Could not create PR from '{}' to '{}'. "
            "It may already exist. Error: {}".format(
                pr_branch, summary.branch, str(e)
            )
        )

    def _apply_fixes(self, gradle_content, fixes):
        # type: (str, List[FixDelta]) -> str
        """Apply version fixes to gradle file content."""
        lines = gradle_content.splitlines(keepends=True)

        for fix in fixes:
            line_num = getattr(fix, "line_number", None)
            if line_num is None:
                continue
            idx = line_num - 1
            if idx < 0 or idx >= len(lines):
                continue

            old_line = lines[idx]
            # Replace only the version string on that line
            new_line = re.sub(
                r"({}:{}):['\"]?[\w.\-+]+['\"]?".format(
                    re.escape(fix.group),
                    re.escape(fix.artifact),
                ),
                r"\1:{}".format(fix.to_version),
                old_line,
            )
            # Fallback — replace version in quoted string
            if new_line == old_line:
                new_line = old_line.replace(
                    ":{}".format(fix.from_version),
                    ":{}".format(fix.to_version),
                )
            lines[idx] = new_line
            logger.info("Fixed {} {} -> {} at line {}".format(
                fix.ga, fix.from_version, fix.to_version, line_num
            ))

        return "".join(lines)