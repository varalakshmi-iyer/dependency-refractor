import re
import difflib
from typing import List, Dict
from backend.core.models import UnusedDependencyResult
from backend.core.github_client import GitHubClient


class PRSubmitter:

    def __init__(self, github_client):
        # type: (GitHubClient) -> None
        self.github = github_client

    def build_modified_gradle(self, original_content, selections):
        # type: (str, List[UnusedDependencyResult]) -> str
        lines           = original_content.splitlines(keepends=True)
        lines_to_remove = set()
        lines_to_move   = {}

        for result in selections:
            ln = result.declaration.line_number - 1
            if result.is_test_only:
                old_line = lines[ln]
                new_line = re.sub(
                    r"^(\s*)(implementation|api|compileOnly)",
                    r"\1testImplementation",
                    old_line,
                )
                lines_to_move[ln] = new_line
            else:
                lines_to_remove.add(ln)

        new_lines = []
        for i, line in enumerate(lines):
            if i in lines_to_remove:
                continue
            elif i in lines_to_move:
                new_lines.append(lines_to_move[i])
            else:
                new_lines.append(line)

        return "".join(new_lines)

    def compute_diff(self, original, modified, file_path):
        # type: (str, str, str) -> str
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile="a/{}".format(file_path),
            tofile="b/{}".format(file_path),
        )
        return "".join(diff)


def submit_pr(self, selections_by_file, base_branch,
              pr_branch, pr_title, pr_description):
    # type: (Dict[str, List[UnusedDependencyResult]], str, str, str, str) -> str

    if not selections_by_file:
        return ""

    # ── Step 1: Discover actual build.gradle paths from repo tree ──────────
    logger.info("Discovering build.gradle paths from repo tree...")
    tree = self.github.get_tree(base_branch)
    actual_gradle_paths = [
        f["path"] for f in tree
        if f["path"].endswith("build.gradle")
        and "buildSrc" not in f["path"]
    ]
    logger.info("Found gradle files: {}".format(actual_gradle_paths))

    # Build lookup: filename/artifact key -> actual full path
    # Match incoming selection key against actual paths
    def resolve_path(incoming_key):
        # type: (str) -> str
        # If it already matches an actual path exactly — use it
        if incoming_key in actual_gradle_paths:
            return incoming_key
        # If incoming is just 'build.gradle' — find best match
        # by checking which actual path ends with the incoming key
        matches = [
            p for p in actual_gradle_paths
            if p.endswith(incoming_key) or p == incoming_key
        ]
        if matches:
            logger.info("Resolved '{}' -> '{}'".format(incoming_key, matches[0]))
            return matches[0]
        # Fall back to first gradle file found
        if actual_gradle_paths:
            logger.warning(
                "Could not resolve '{}' — falling back to '{}'".format(
                    incoming_key, actual_gradle_paths[0]
                )
            )
            return actual_gradle_paths[0]
        raise RuntimeError(
            "No build.gradle files found in repo on branch '{}'".format(
                base_branch
            )
        )

    # ── Step 2: Get base branch HEAD SHA ───────────────────────────────────
    head_sha = self.github.get_branch_sha(base_branch)
    logger.info("HEAD SHA: {}".format(head_sha))

    # ── Step 3: Create PR branch ───────────────────────────────────────────
    self.github.create_branch(pr_branch, head_sha)
    logger.info("Branch created: {}".format(pr_branch))

    # ── Step 4: Commit each modified gradle file ───────────────────────────
    committed = []
    for incoming_path, selections in selections_by_file.items():

        actual_path = resolve_path(incoming_path)
        logger.info("Committing: '{}' (resolved from '{}')".format(
            actual_path, incoming_path
        ))

        original = self.github.get_file_content(actual_path, base_branch)
        modified = self.build_modified_gradle(original, selections)
        file_sha = self.github.get_file_sha(actual_path, base_branch)

        removed  = [r for r in selections if r.is_unused]
        moved    = [r for r in selections if r.is_test_only]

        msg_parts = []
        if removed:
            msg_parts.append("remove {} unused dep(s)".format(len(removed)))
        if moved:
            msg_parts.append("move {} to testImplementation".format(len(moved)))

        commit_msg = "chore(deps): {} in {}".format(
            ", ".join(msg_parts) or "fix dependencies",
            actual_path,
        )

        self.github.commit_file(
            path=actual_path,
            new_content=modified,
            branch=pr_branch,
            message=commit_msg,
            file_sha=file_sha,
        )
        logger.info("Committed: {}".format(actual_path))
        committed.append((actual_path, removed, moved))

    # ── Step 5: Open PR ────────────────────────────────────────────────────
    body_lines = [pr_description, "", "---", "### Changes", ""]
    for actual_path, removed, moved in committed:
        body_lines.append("**`{}`**".format(actual_path))
        for r in removed:
            body_lines.append("- Removed `{}` — {}".format(
                r.declaration.gav, r.reason
            ))
        for r in moved:
            body_lines.append("- Moved `{}` to testImplementation — {}".format(
                r.declaration.gav, r.reason
            ))
        body_lines.append("")
    body_lines.append("_Generated by dependency_refractor_")

    pr_url = self.github.create_pr(
        title=pr_title,
        body="\n".join(body_lines),
        head_branch=pr_branch,
        base_branch=base_branch,
    )
    logger.info("PR created: {}".format(pr_url))
    return pr_url