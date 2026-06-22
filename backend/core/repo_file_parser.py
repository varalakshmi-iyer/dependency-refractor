import logging
from typing import List

logger = logging.getLogger("dependency_refractor.repo_parser")


class RepoFileParser:
    """
    Parses a ~ delimited .txt file of GitHub repo URLs.

    File format:
        https://github.com/org/service-b~https://github.com/org/service-c~...

    Supports:
      - Single line ~ delimited
      - Multi-line ~ delimited
      - Strips whitespace and empty entries
      - Validates GitHub URL format
    """

    DELIMITER = "~"

    def parse(self, content):
        # type: (str) -> List[str]
        """Parse file content and return list of clean repo URLs."""
        raw   = content.replace("\n", self.DELIMITER)
        parts = raw.split(self.DELIMITER)

        repos = []
        for part in parts:
            url = part.strip()
            if not url:
                continue
            if not url.startswith("https://github.com/"):
                logger.warning("Skipping invalid URL: {}".format(url))
                continue
            # Normalize — strip trailing slash
            url = url.rstrip("/")
            repos.append(url)

        logger.info("Parsed {} target repos from file".format(len(repos)))
        for r in repos:
            logger.info("  Target: {}".format(r))

        return repos

    def parse_bytes(self, content_bytes):
        # type: (bytes) -> List[str]
        """Parse uploaded file bytes."""
        return self.parse(content_bytes.decode("utf-8", errors="replace"))

    def repo_name(self, url):
        # type: (str) -> str
        """Extract org/repo from full GitHub URL."""
        return url.replace("https://github.com/", "").rstrip("/")