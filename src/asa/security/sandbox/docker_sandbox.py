"""Docker-based sandbox for isolating repository analysis.

Repositories must be analyzed inside isolated Docker environments.
Never execute untrusted repository code directly on the host.
"""

from __future__ import annotations

import os
from typing import Any

from asa.config.settings import Settings, get_settings
from asa.core.logging import get_logger

logger = get_logger("asa.sandbox")


class DockerSandbox:
    """Manages Docker containers for isolated repository analysis."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    @property
    def available(self) -> bool:
        """Check if Docker is available."""
        if not self.settings.docker_enabled:
            return False
        try:
            import docker
            self._client = docker.from_env()
            self._client.ping()
            return True
        except Exception:
            return False

    def create_analysis_container(
        self,
        repo_path: str,
        command: str = "echo 'Analysis complete'",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Create and run a container for isolated analysis.

        Args:
            repo_path: Path to the repository to analyze.
            command: Command to run inside the container.
            timeout: Override timeout in seconds.

        Returns:
            Container result with stdout, stderr, and exit code.
        """
        if not self.available:
            logger.warning("sandbox.docker_unavailable")
            return {
                "success": False,
                "error": "Docker not available",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }

        timeout = timeout or self.settings.docker_timeout

        try:
            import docker
            container = self._client.containers.run(
                self.settings.docker_image,
                command=command,
                volumes={
                    repo_path: {"bind": "/repo", "mode": "readonly"},
                },
                network_disabled=True,
                mem_limit=self.settings.docker_memory_limit,
                cpu_quota=int(self.settings.docker_cpu_limit * 100000),
                detach=True,
                labels={"asa-managed": "true"},
            )

            # Wait for completion
            result = container.wait(timeout=timeout)
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            # Cleanup
            container.remove(force=True)

            return {
                "success": result.get("StatusCode", 1) == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.get("StatusCode", -1),
            }

        except Exception as e:
            logger.error("sandbox.container_error", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }

    def cleanup(self) -> None:
        """Remove all ASA-managed containers."""
        if not self.available or self._client is None:
            return

        try:
            containers = self._client.containers.list(
                all=True,
                filters={"label": "asa-managed=true"},
            )
            for container in containers:
                container.remove(force=True)
                logger.info("sandbox.container_removed", id=container.short_id)
        except Exception as e:
            logger.error("sandbox.cleanup_error", error=str(e))
