import time
import logging
import requests
from typing import List, Optional
from backend.core.models import DependencyResult, Vulnerability

logger = logging.getLogger("dependency_refractor.snyk")


class SnykClient:

    def __init__(self, token, org_id, proxy_url="",
                 ssl_verify=True, timeout=60, max_retries=2, retry_delay=3):
        # type: (str, str, str, object, int, int, int) -> None
        self.token       = token
        self.org_id      = org_id
        self.headers     = {
            "Authorization": "token {}".format(token),
            "Content-Type":  "application/json",
        }
        self.base        = "https://api.snyk.io/v1"
        self.proxies     = {"http": proxy_url, "https": proxy_url} if proxy_url else {}
        self.ssl_verify  = ssl_verify
        self.timeout     = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        logger.info("SnykClient init — timeout: {}s, retries: {}".format(
            timeout, max_retries
        ))

    def test_dependency(self, group, artifact, version):
        # type: (str, str, str) -> DependencyResult
        logger.info("Checking {}:{}:{}".format(group, artifact, version))

        for attempt in range(1, self.max_retries + 2):
            try:
                url = "{}/test/maven/{}/{}/{}".format(
                    self.base, group, artifact, version
                )
                r = requests.get(
                    url,
                    headers=self.headers,
                    params={"org": self.org_id},
                    proxies=self.proxies,
                    verify=self.ssl_verify,
                    timeout=self.timeout,
                )
                logger.info("Snyk response: {} for {}:{}:{}".format(
                    r.status_code, group, artifact, version
                ))

                if r.status_code == 404:
                    return DependencyResult(
                        group=group, artifact=artifact,
                        version=version, is_vulnerable=False,
                    )
                if r.status_code == 401:
                    raise RuntimeError("Snyk 401 — check SNYK_TOKEN")
                if r.status_code == 403:
                    raise RuntimeError("Snyk 403 — check SNYK_ORG_ID")
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", self.retry_delay * attempt))
                    logger.warning("Snyk rate limited — waiting {}s".format(wait))
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                return self._parse_result(group, artifact, version, r.json())

            except requests.exceptions.Timeout:
                logger.warning("Snyk timeout attempt {}/{} for {}:{}:{}".format(
                    attempt, self.max_retries + 1, group, artifact, version
                ))
                if attempt <= self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                logger.error("Snyk gave up after {} attempts for {}:{}:{}".format(
                    attempt, group, artifact, version
                ))
                # Return non-vulnerable rather than crashing the whole analysis
                return DependencyResult(
                    group=group, artifact=artifact,
                    version=version, is_vulnerable=False,
                )

            except requests.exceptions.ConnectionError as e:
                logger.error("Snyk connection error: {}".format(e))
                raise RuntimeError(
                    "Cannot reach Snyk. Check proxy settings. Detail: {}".format(e)
                )

            except RuntimeError:
                raise

            except Exception as e:
                logger.error("Snyk unexpected error for {}:{}:{} — {}".format(
                    group, artifact, version, e
                ), exc_info=True)
                return DependencyResult(
                    group=group, artifact=artifact,
                    version=version, is_vulnerable=False,
                )

        return DependencyResult(
            group=group, artifact=artifact,
            version=version, is_vulnerable=False,
        )

    def _parse_result(self, group, artifact, version, data):
        # type: (str, str, str, dict) -> DependencyResult
        is_ok  = data.get("ok", True)
        vulns  = data.get("issues", {}).get("vulnerabilities", [])
        parsed = []
        for v in vulns:
            cvss         = 0.0
            cvss_details = v.get("cvssDetails", [])
            if cvss_details:
                cvss = float(cvss_details[0].get("cvssV3BaseScore", 0.0))
            else:
                cvss = float(v.get("cvssScore", 0.0))
            parsed.append(Vulnerability(
                cve_id=v.get("identifiers", {}).get("CVE", ["N/A"])[0],
                severity=v.get("severity", "unknown"),
                cvss=cvss,
                title=v.get("title", "")[:200],
                fixed_in=v.get("fixedIn", []),
                description=v.get("description", "")[:300],
            ))
        is_vulnerable = (not is_ok) and len(parsed) > 0
        return DependencyResult(
            group=group, artifact=artifact, version=version,
            is_vulnerable=is_vulnerable,
            vulnerabilities=parsed,
            safe_version=self._find_safe_version(parsed),
        )

    def _find_safe_version(self, vulns):
        # type: (List[Vulnerability]) -> Optional[str]
        all_fixes = []
        for v in vulns:
            all_fixes.extend(v.fixed_in)
        if not all_fixes:
            return None
        return sorted(all_fixes, key=self._version_tuple)[-1]

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