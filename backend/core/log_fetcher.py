import os
import subprocess
from pathlib import Path
from typing import Optional


class LogFetcher:
    """
    Fetches build log via OC client subprocess.
    TODO: update OC_COMMAND once you confirm the exact oc command.
    """

    # TODO: replace with your actual oc command
    # Placeholders: {build_id}, {namespace}, {output_path}
    OC_COMMAND_TEMPLATE = "oc logs build/{build_id} -n {namespace} > {output_path}"

    def fetch_via_oc(self, build_id, namespace="default",
                     output_path="/tmp/build.log"):
        # type: (str, str, str) -> str
        """
        Runs OC client command to fetch build log.
        Returns log content as string.
        """
        cmd = self.OC_COMMAND_TEMPLATE.format(
            build_id=build_id,
            namespace=namespace,
            output_path=output_path,
        )

        print("[LogFetcher] Running: {}".format(cmd))

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "OC command failed (exit {}): {}".format(
                        result.returncode, result.stderr[:300]
                    )
                )

            p = Path(output_path)
            if not p.exists():
                raise FileNotFoundError(
                    "Log file not found at '{}' after oc command".format(output_path)
                )

            content = p.read_text()
            print("[LogFetcher] Fetched {} lines".format(len(content.splitlines())))
            return content

        except subprocess.TimeoutExpired:
            raise RuntimeError("OC command timed out after 120s")

    def read_uploaded_file(self, file_content):
        # type: (bytes) -> str
        """Decodes an uploaded .log or .txt file."""
        return file_content.decode("utf-8", errors="replace")