from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ResolvedDependency:
    group:    str
    artifact: str
    version:  str
    depth:    int
    status:   str
    parent:   Optional[str] = None

    @property
    def ga(self):
        # type: () -> str
        return "{}:{}".format(self.group, self.artifact)

    @property
    def gav(self):
        # type: () -> str
        return "{}:{}:{}".format(self.group, self.artifact, self.version)

    @property
    def is_root(self):
        # type: () -> bool
        return self.status == "UNKNOWN"


@dataclass
class Vulnerability:
    cve_id:      str
    severity:    str
    cvss:        float
    title:       str
    fixed_in:    List[str]
    description: str = ""


@dataclass
class DependencyResult:
    group:           str
    artifact:        str
    version:         str
    is_vulnerable:   bool
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    safe_version:    Optional[str] = None

    @property
    def gav(self):
        # type: () -> str
        return "{}:{}:{}".format(self.group, self.artifact, self.version)


@dataclass
class ConflictEntry:
    ga:                    str
    all_versions:          List[str]
    resolved_version:      str
    sources:               List[str]
    version_vuln_map:      Dict[str, DependencyResult] = field(default_factory=dict)
    recommended_version:   Optional[str] = None
    recommendation_reason: str = ""


@dataclass
class ConflictIssue:
    severity:       str
    entry:          ConflictEntry
    recommendation: str


@dataclass
class GradleDependencyDeclaration:
    group:         str
    artifact:      str
    version:       str
    configuration: str
    raw_line:      str
    line_number:   int

    @property
    def ga(self):
        # type: () -> str
        return "{}:{}".format(self.group, self.artifact)

    @property
    def gav(self):
        # type: () -> str
        return "{}:{}:{}".format(self.group, self.artifact, self.version)


@dataclass
class UnusedDependencyResult:
    declaration:    GradleDependencyDeclaration
    gradle_file:    str
    is_unused:      bool
    is_test_only:   bool
    import_matches: List[str]
    confidence:     str
    reason:         str


@dataclass
class AnalysisResult:
    service_name:     str
    branch_name:      str
    conflict_issues:  List[ConflictIssue]
    vuln_results:     List[DependencyResult]
    unused_results:   Dict[str, List[UnusedDependencyResult]]
    all_deps:         List[ResolvedDependency]
    html_report:      str
    errors:           List[str] = field(default_factory=list)