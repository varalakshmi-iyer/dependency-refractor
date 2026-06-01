import re
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional
from backend.core.models import (
    ResolvedDependency, ConflictIssue, ConflictEntry, DependencyResult
)
from backend.core.snyk_client import SnykClient


class ConflictAnalyzer:

    def __init__(self, snyk_client):
        # type: (SnykClient) -> None
        self.snyk = snyk_client

    def analyze(self, deps):
        # type: (List[ResolvedDependency]) -> List[ConflictIssue]
        versions_seen   = defaultdict(set)
        version_sources = defaultdict(list)

        for dep in deps:
            versions_seen[dep.ga].add(dep.version)
            key = "{}:{}".format(dep.ga, dep.version)
            if dep.parent:
                version_sources[key].append(dep.parent)

        issues = []
        for ga, versions in versions_seen.items():
            if len(versions) <= 1:
                continue

            all_v    = sorted(versions, key=self._version_tuple)
            sources  = self._collect_sources(ga, versions, version_sources)
            severity = self._severity(all_v)

            group, artifact  = ga.split(":", 1)
            version_vuln_map = {}
            for v in all_v:
                version_vuln_map[v] = self.snyk.test_dependency(
                    group, artifact, v
                )

            recommended, reason = self._recommend(all_v, version_vuln_map)

            issues.append(ConflictIssue(
                severity=severity,
                entry=ConflictEntry(
                    ga=ga,
                    all_versions=all_v,
                    resolved_version=all_v[-1],
                    sources=sources,
                    version_vuln_map=version_vuln_map,
                    recommended_version=recommended,
                    recommendation_reason=reason,
                ),
                recommendation="Pin to {}. {}".format(recommended, reason),
            ))

        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
        issues.sort(key=lambda i: order.get(i.severity, 9))
        return issues

    def _recommend(self, versions, vuln_map):
        # type: (List[str], Dict[str, DependencyResult]) -> Tuple[str, str]
        clean = [v for v in versions if not vuln_map[v].is_vulnerable]
        if clean:
            best = sorted(clean, key=self._version_tuple)[-1]
            return best, "Non-vulnerable — safe to pin."
        for v in sorted(versions, key=self._version_tuple, reverse=True):
            fix = vuln_map[v].safe_version
            if fix:
                return fix, "All versions vulnerable. Upgrade to {}.".format(fix)
        best = sorted(versions, key=self._version_tuple)[-1]
        return best, "All versions vulnerable, no known fix. Use latest and monitor."

    def _severity(self, versions):
        # type: (List[str]) -> str
        majors = set()
        for v in versions:
            m = re.match(r"(\d+)", v)
            if m:
                majors.add(int(m.group(1)))
        return "CRITICAL" if len(majors) > 1 else "HIGH"

    def _version_tuple(self, version):
        # type: (str) -> tuple
        parts  = re.split(r"[.\-]", version)
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                result.append(0)
        return tuple(result)

    def _collect_sources(self, ga, versions, version_sources):
        # type: (str, Set[str], Dict) -> List[str]
        found = set()
        for v in versions:
            key = "{}:{}".format(ga, v)
            for src in version_sources.get(key, []):
                found.add(src)
        return sorted(found)