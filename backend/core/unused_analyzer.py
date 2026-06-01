import re
from typing import List, Dict, Set
from backend.core.models import (
    GradleDependencyDeclaration, UnusedDependencyResult
)
from backend.core.github_client import GitHubClient


class UnusedDependencyAnalyzer:

    TARGET_CONFIGS = {"implementation", "api", "compileOnly"}

    ARTIFACT_PACKAGE_MAP = {
        "guava":                    ["com.google.common"],
        "jackson-databind":         ["com.fasterxml.jackson.databind"],
        "jackson-core":             ["com.fasterxml.jackson.core"],
        "jackson-annotations":      ["com.fasterxml.jackson.annotation"],
        "log4j-core":               ["org.apache.logging.log4j"],
        "log4j-api":                ["org.apache.logging.log4j"],
        "slf4j-api":                ["org.slf4j"],
        "logback-classic":          ["ch.qos.logback"],
        "commons-lang":             ["org.apache.commons.lang"],
        "commons-lang3":            ["org.apache.commons.lang3"],
        "commons-io":               ["org.apache.commons.io"],
        "okhttp":                   ["okhttp3"],
        "gson":                     ["com.google.gson"],
        "lombok":                   ["lombok"],
        "mapstruct":                ["org.mapstruct"],
        "micrometer-core":          ["io.micrometer"],
        "micrometer-jakarta":       ["io.micrometer"],
        "spring-boot-starter-web":  ["org.springframework.web",
                                     "org.springframework.boot"],
        "spring-boot-starter-data-jpa": ["org.springframework.data",
                                         "jakarta.persistence"],
        "junit":                    ["org.junit", "junit"],
        "mockito-core":             ["org.mockito"],
        "h2":                       ["org.h2"],
        "postgresql":               ["org.postgresql"],
        "reactor-core":             ["reactor.core"],
    }

    TEST_ONLY_ARTIFACTS = {
        "junit", "mockito-core", "mockito-junit-jupiter",
        "spring-boot-starter-test", "assertj-core",
        "hamcrest", "testcontainers", "h2",
    }

    GRADLE_DEP_RE = re.compile(
        r"(?P<config>implementation|api|compileOnly)"
        r"\s+['\"](?P<group>[\w.\-]+):(?P<artifact>[\w.\-]+)"
        r":(?P<version>[\w.\-+${}]+)['\"]"
    )

    IMPORT_RE = re.compile(r"^\s*import\s+([\w.]+)\s*;", re.MULTILINE)

    def __init__(self, github_client):
        # type: (GitHubClient) -> None
        self.github = github_client

    def analyze(self, branch):
        # type: (str) -> Dict[str, List[UnusedDependencyResult]]
        tree = self.github.get_tree(branch)

        gradle_files = [
            f["path"] for f in tree
            if f["path"].endswith("build.gradle")
            and "buildSrc" not in f["path"]
        ]
        main_java = [
            f["path"] for f in tree
            if f["path"].endswith(".java")
            and "/test/" not in f["path"]
        ]
        test_java = [
            f["path"] for f in tree
            if f["path"].endswith(".java")
            and "/test/" in f["path"]
        ]

        main_imports = self._collect_imports(main_java, branch)
        test_imports = self._collect_imports(test_java, branch)

        results = {}
        for gradle_path in gradle_files:
            content  = self.github.get_file_content(gradle_path, branch)
            declared = self._parse_gradle(content, gradle_path)
            file_results = []
            for decl in declared:
                result = self._check_usage(
                    decl, gradle_path, main_imports, test_imports
                )
                if result.is_unused or result.is_test_only:
                    file_results.append(result)
            if file_results:
                results[gradle_path] = file_results

        return results

    def _parse_gradle(self, content, gradle_path):
        # type: (str, str) -> List[GradleDependencyDeclaration]
        decls = []
        for line_num, line in enumerate(content.splitlines(), 1):
            m = self.GRADLE_DEP_RE.search(line)
            if not m:
                continue
            if m.group("config") not in self.TARGET_CONFIGS:
                continue
            decls.append(GradleDependencyDeclaration(
                group=m.group("group"),
                artifact=m.group("artifact"),
                version=m.group("version"),
                configuration=m.group("config"),
                raw_line=line,
                line_number=line_num,
            ))
        return decls

    def _collect_imports(self, java_files, branch):
        # type: (List[str], str) -> Set[str]
        all_imports = set()
        for path in java_files:
            try:
                content = self.github.get_file_content(path, branch)
                for m in self.IMPORT_RE.finditer(content):
                    all_imports.add(m.group(1))
            except Exception:
                pass
        return all_imports

    def _check_usage(self, decl, gradle_path, main_imports, test_imports):
        # type: (GradleDependencyDeclaration, str, Set[str], Set[str]) -> UnusedDependencyResult
        patterns     = self._get_patterns(decl.artifact)
        main_matches = self._find_matches(patterns, main_imports)
        test_matches = self._find_matches(patterns, test_imports)
        is_known_test = decl.artifact.lower() in self.TEST_ONLY_ARTIFACTS

        if not patterns:
            return UnusedDependencyResult(
                declaration=decl, gradle_file=gradle_path,
                is_unused=False, is_test_only=False,
                import_matches=[], confidence="LOW",
                reason="No package mapping for '{}' — manual review needed.".format(
                    decl.artifact
                ),
            )

        if main_matches:
            return UnusedDependencyResult(
                declaration=decl, gradle_file=gradle_path,
                is_unused=False, is_test_only=False,
                import_matches=main_matches, confidence="HIGH",
                reason="Used in {} main source file(s).".format(len(main_matches)),
            )

        if test_matches or is_known_test:
            return UnusedDependencyResult(
                declaration=decl, gradle_file=gradle_path,
                is_unused=False, is_test_only=True,
                import_matches=test_matches, confidence="HIGH",
                reason=(
                    "Found only in test source — move to testImplementation."
                    if test_matches else
                    "Known test-only library in '{}' scope.".format(decl.configuration)
                ),
            )

        return UnusedDependencyResult(
            declaration=decl, gradle_file=gradle_path,
            is_unused=True, is_test_only=False,
            import_matches=[], confidence="MEDIUM",
            reason="No import of {} found anywhere.".format(
                " or ".join(patterns)
            ),
        )

    def _get_patterns(self, artifact):
        # type: (str) -> List[str]
        key = artifact.lower()
        if key in self.ARTIFACT_PACKAGE_MAP:
            return self.ARTIFACT_PACKAGE_MAP[key]
        for map_key, patterns in self.ARTIFACT_PACKAGE_MAP.items():
            if key.startswith(map_key) or map_key.startswith(key):
                return patterns
        return []

    def _find_matches(self, patterns, imports):
        # type: (List[str], Set[str]) -> List[str]
        matches = []
        for imp in imports:
            for pattern in patterns:
                if imp.startswith(pattern):
                    matches.append(imp)
                    break
        return sorted(set(matches))