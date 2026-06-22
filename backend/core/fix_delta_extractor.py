import logging
from typing import List, Dict
from backend.core.models import ConflictIssue, DependencyResult

logger = logging.getLogger("dependency_refractor.fix_delta")


class FixDelta:
    """
    Represents a single version fix recommendation.
    from_version : what was found in the source repo
    to_version   : what Snyk recommends
    reason       : why this version was chosen
    cve_ids      : CVEs that drove this recommendation
    """

    def __init__(self, ga, from_version, to_version, reason, cve_ids=None):
        # type: (str, str, str, str, List[str]) -> None
        self.ga           = ga               # group:artifact
        self.from_version = from_version
        self.to_version   = to_version
        self.reason       = reason
        self.cve_ids      = cve_ids or []

    @property
    def group(self):
        # type: () -> str
        return self.ga.split(":")[0]

    @property
    def artifact(self):
        # type: () -> str
        return self.ga.split(":")[1] if ":" in self.ga else self.ga

    def __repr__(self):
        return "FixDelta({} {} -> {})".format(
            self.ga, self.from_version, self.to_version
        )


class FixDeltaExtractor:
    """
    Extracts the fix delta from analysis results.

    Two sources of fixes:
    1. Conflict resolution — Snyk recommended a safe version among conflicting ones
    2. Vulnerability scan  — Snyk found CVEs and recommended a safe version

    Output: list of FixDelta objects representing what needs to change.
    """

    def extract(self, conflict_issues, vuln_results):
        # type: (List[ConflictIssue], List[DependencyResult]) -> List[FixDelta]
        deltas = {}   # type: Dict[str, FixDelta]   # ga -> FixDelta

        # ── Source 1: Conflict resolution fixes ───────────────────────────
        for issue in conflict_issues:
            e = issue.entry
            if not e.recommended_version:
                continue

            # The "from" is the highest version currently in the tree
            from_version = e.resolved_version
            to_version   = e.recommended_version

            if from_version == to_version:
                continue

            cve_ids = []
            for v, result in e.version_vuln_map.items():
                for vuln in result.vulnerabilities:
                    if vuln.cve_id not in cve_ids:
                        cve_ids.append(vuln.cve_id)

            delta = FixDelta(
                ga=e.ga,
                from_version=from_version,
                to_version=to_version,
                reason=e.recommendation_reason,
                cve_ids=cve_ids,
            )
            deltas[e.ga] = delta
            logger.info("Conflict fix: {} {} -> {}".format(
                e.ga, from_version, to_version
            ))

        # ── Source 2: Vulnerability scan fixes ────────────────────────────
        for result in vuln_results:
            if not result.is_vulnerable:
                continue
            if not result.safe_version:
                continue

            ga           = result.ga
            from_version = result.version
            to_version   = result.safe_version

            if from_version == to_version:
                continue

            # Don't overwrite a conflict fix with a weaker vuln fix
            if ga in deltas:
                continue

            cve_ids = [v.cve_id for v in result.vulnerabilities]
            reason  = "Snyk found {} CVE(s): {}. Safe version: {}.".format(
                len(cve_ids),
                ", ".join(cve_ids[:3]) + ("..." if len(cve_ids) > 3 else ""),
                to_version,
            )

            delta = FixDelta(
                ga=ga,
                from_version=from_version,
                to_version=to_version,
                reason=reason,
                cve_ids=cve_ids,
            )
            deltas[ga] = delta
            logger.info("Vuln fix: {} {} -> {}".format(
                ga, from_version, to_version
            ))

        result_list = list(deltas.values())
        logger.info("Total fix deltas extracted: {}".format(len(result_list)))
        return result_list