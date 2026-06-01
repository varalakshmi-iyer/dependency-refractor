import base64
import requests
from typing import List, Optional
from backend.core.models import UnusedDependencyResult


class GitHubClient:

    BASE = "https://api.github.com"

    def __init__(self, pat, repo, proxy_url="",
                 ssl_verify=True, timeout=60):
        # type: (str, str, str, object, int) -> None
        self.pat      = pat
        self.repo     = repo
        self.headers  = {
            "Authorization":        "Bearer {}".format(pat),
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.proxies   = {"http": proxy_url, "https": proxy_url} if proxy_url else {}
        self.ssl_verify = ssl_verify
        self.timeout   = timeout

    def _get(self, path, params=None):
        # type: (str, dict) -> dict
        url = "{}/repos/{}{}".format(self.BASE, self.repo, path)
        r   = requests.get(
            url, headers=self.headers, params=params,
            proxies=self.proxies, verify=self.ssl_verify,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path, payload):
        # type: (str, dict) -> dict
        url = "{}/repos/{}{}".format(self.BASE, self.repo, path)
        r   = requests.post(
            url, headers=self.headers, json=payload,
            proxies=self.proxies, verify=self.ssl_verify,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def _put(self, path, payload):
        # type: (str, dict) -> dict
        url = "{}/repos/{}{}".format(self.BASE, self.repo, path)
        r   = requests.put(
            url, headers=self.headers, json=payload,
            proxies=self.proxies, verify=self.ssl_verify,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get_tree(self, branch):
        # type: (str) -> List[dict]
        data = self._get(
            "/git/trees/{}".format(branch),
            params={"recursive": "1"},
        )
        return [
            item for item in data.get("tree", [])
            if item.get("type") == "blob"
        ]

    def get_file_content(self, path, branch):
        # type: (str, str) -> str
        data    = self._get(
            "/contents/{}".format(path),
            params={"ref": branch},
        )
        content = data.get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="replace")

    def get_file_sha(self, path, branch):
        # type: (str, str) -> str
        data = self._get(
            "/contents/{}".format(path),
            params={"ref": branch},
        )
        return data.get("sha", "")

    def get_branch_sha(self, branch):
        # type: (str) -> str
        data = self._get("/branches/{}".format(branch))
        return data["commit"]["sha"]

    def create_branch(self, new_branch, from_sha):
        # type: (str, str) -> None
        self._post("/git/refs", {
            "ref": "refs/heads/{}".format(new_branch),
            "sha": from_sha,
        })

    def commit_file(self, path, new_content, branch, message, file_sha):
        # type: (str, str, str, str, str) -> None
        self._put("/contents/{}".format(path), {
            "message": message,
            "content": base64.b64encode(
                new_content.encode("utf-8")
            ).decode("ascii"),
            "branch":  branch,
            "sha":     file_sha,
        })

    def create_pr(self, title, body, head_branch, base_branch):
        # type: (str, str, str, str) -> str
        data = self._post("/pulls", {
            "title": title,
            "body":  body,
            "head":  head_branch,
            "base":  base_branch,
        })
        return data.get("html_url", "")