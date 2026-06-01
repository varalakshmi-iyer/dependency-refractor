import re
from typing import List, Dict
from backend.core.models import ResolvedDependency


class BuildLogParser:
    """
    Parses pkg:mvn dependency tree format:

        pkg:mvn/com.example/service@1.0.0?type=jar -> UNKNOWN
        -  pkg:mvn/com.google.guava/guava@32.1.2?type=jar -> NONE
        -  -  pkg:mvn/com.google.guava/failureaccess@1.0.1?type=jar -> NONE
    """

    LINE_RE = re.compile(
        r"^((?:-\s+)*)"
        r"pkg:mvn/([^/]+)/([^@]+)"
        r"@([^?]+)"
        r"(?:\?[^\s]*)?"
        r"\s+->\s+(UNKNOWN|NONE)"
    )

    def parse(self, log_text):
        # type: (str) -> List[ResolvedDependency]
        deps         = []
        parent_stack = {}   # type: Dict[int, str]

        for line in log_text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = self.LINE_RE.match(line)
            if not m:
                continue

            prefix   = m.group(1) or ""
            group    = m.group(2).strip()
            artifact = m.group(3).strip()
            version  = m.group(4).strip()
            status   = m.group(5).strip()
            depth    = prefix.count("-")
            ga       = "{}:{}".format(group, artifact)
            parent   = parent_stack.get(depth - 1) if depth > 0 else None

            deps.append(ResolvedDependency(
                group=group, artifact=artifact, version=version,
                depth=depth, status=status, parent=parent,
            ))

            parent_stack[depth] = ga
            for k in [k for k in parent_stack if k > depth]:
                del parent_stack[k]

        return deps