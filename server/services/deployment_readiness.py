from __future__ import annotations

import os
import subprocess
from pathlib import Path


class DeploymentReadiness:
    REQUIRED_ENV_VARS = [
        ("NEXUS_RUNTIME_HOST_BASE_URL", "Runtime host relay base URL", False),
        ("NEXUS_RUNTIME_HOST_SHARED_TOKEN", "Runtime host relay authentication token", False),
        ("NEXUS_REPLICA_PACKS_ROOT", "Path to bounded replica packs directory", False),
    ]

    @staticmethod
    def check_docker_available() -> dict[str, object]:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return {
                    "available": True,
                    "version": result.stdout.strip(),
                    "message": "Docker is available and executable.",
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "message": "Docker command failed: check installation and permissions.",
                }
        except FileNotFoundError:
            return {
                "available": False,
                "version": None,
                "message": "Docker command not found. Install Docker or add it to PATH.",
            }
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "version": None,
                "message": "Docker health check timed out.",
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "message": f"Docker check failed: {str(e)}",
            }

    @staticmethod
    def check_runtime_host_relay() -> dict[str, object]:
        base_url = os.getenv("NEXUS_RUNTIME_HOST_BASE_URL", "").strip()
        shared_token = os.getenv("NEXUS_RUNTIME_HOST_SHARED_TOKEN", "").strip()

        if not base_url or not shared_token:
            return {
                "configured": False,
                "reachable": False,
                "complete": False,
                "message": "Runtime host relay is not configured (required env vars missing).",
                "missing_config": [
                    "NEXUS_RUNTIME_HOST_BASE_URL" if not base_url else None,
                    "NEXUS_RUNTIME_HOST_SHARED_TOKEN" if not shared_token else None,
                ],
            }

        try:
            from urllib.request import Request as UrlRequest, urlopen
            from urllib.error import URLError

            request = UrlRequest(f"{base_url.rstrip('/')}/health", method="GET")
            with urlopen(request, timeout=2) as response:
                is_healthy = response.status == 200
                return {
                    "configured": True,
                    "reachable": is_healthy,
                    "complete": is_healthy,
                    "message": (
                        "Runtime host relay is reachable and healthy."
                        if is_healthy
                        else "Runtime host relay is reachable but reported unhealthy status."
                    ),
                    "base_url": base_url,
                }
        except URLError as error:
            reason = getattr(error, "reason", None)
            reason_text = str(reason or error).strip() or "connection failed"
            return {
                "configured": True,
                "reachable": False,
                "complete": False,
                "message": f"Runtime host relay is not reachable: {reason_text}",
                "base_url": base_url,
            }
        except Exception as e:
            return {
                "configured": True,
                "reachable": False,
                "complete": False,
                "message": f"Failed to check runtime host relay: {str(e)}",
                "base_url": base_url,
            }

    @staticmethod
    def check_pack_root() -> dict[str, object]:
        pack_root = os.getenv("NEXUS_REPLICA_PACKS_ROOT", "").strip()
        if not pack_root:
            return {
                "configured": False,
                "accessible": False,
                "pack_count": 0,
                "message": "Pack root directory is not configured (NEXUS_REPLICA_PACKS_ROOT missing).",
            }

        pack_path = Path(pack_root)
        if not pack_path.exists():
            return {
                "configured": True,
                "path": pack_root,
                "accessible": False,
                "pack_count": 0,
                "message": f"Pack root directory does not exist: {pack_root}",
            }

        if not pack_path.is_dir():
            return {
                "configured": True,
                "path": pack_root,
                "accessible": False,
                "pack_count": 0,
                "message": f"Pack root is not a directory: {pack_root}",
            }

        try:
            pack_dirs = [d for d in pack_path.iterdir() if d.is_dir()]
            return {
                "configured": True,
                "path": pack_root,
                "accessible": True,
                "pack_count": len(pack_dirs),
                "message": f"Pack root is accessible with {len(pack_dirs)} pack(s) present.",
                "packs": [d.name for d in pack_dirs],
            }
        except PermissionError:
            return {
                "configured": True,
                "path": pack_root,
                "accessible": False,
                "pack_count": 0,
                "message": f"Pack root is not readable (permission denied): {pack_root}",
            }
        except Exception as e:
            return {
                "configured": True,
                "path": pack_root,
                "accessible": False,
                "pack_count": 0,
                "message": f"Failed to check pack root: {str(e)}",
            }

    @staticmethod
    def check_required_env_vars() -> dict[str, object]:
        missing_vars = []
        for var_name, var_label, is_required in DeploymentReadiness.REQUIRED_ENV_VARS:
            if is_required and not os.getenv(var_name, "").strip():
                missing_vars.append({"name": var_name, "label": var_label, "required": True})

        if missing_vars:
            return {
                "all_present": False,
                "all_required_present": False,
                "missing_required": missing_vars,
                "message": f"Missing {len(missing_vars)} required environment variable(s).",
            }

        return {
            "all_present": True,
            "all_required_present": True,
            "missing_required": [],
            "message": "All required environment variables are present.",
        }

    @staticmethod
    def get_deployment_readiness() -> dict[str, object]:
        docker_status = DeploymentReadiness.check_docker_available()
        runtime_host_status = DeploymentReadiness.check_runtime_host_relay()
        pack_root_status = DeploymentReadiness.check_pack_root()
        env_vars_status = DeploymentReadiness.check_required_env_vars()

        # Determine overall readiness
        fully_ready = (
            docker_status.get("available", False)
            and runtime_host_status.get("complete", False)
            and pack_root_status.get("accessible", False)
            and env_vars_status.get("all_required_present", False)
        )

        partially_ready = (
            (docker_status.get("available", False) or pack_root_status.get("accessible", False))
            and not fully_ready
        )

        readiness_status = "fully_available" if fully_ready else ("partially_available" if partially_ready else "unavailable")

        degraded_features = []
        if not docker_status.get("available", False):
            degraded_features.append("Docker-backed bounded replay is unavailable")
        if not runtime_host_status.get("complete", False):
            degraded_features.append("Runtime host relay is unavailable")
        if not pack_root_status.get("accessible", False):
            degraded_features.append("Bounded REPLICA packs are unavailable")

        return {
            "readiness": readiness_status,
            "fully_available": fully_ready,
            "partially_available": partially_ready,
            "docker": docker_status,
            "runtime_host_relay": runtime_host_status,
            "pack_root": pack_root_status,
            "required_env_vars": env_vars_status,
            "degraded_features": degraded_features,
            "message": (
                "Deployment is fully ready for production use."
                if fully_ready
                else (
                    f"Deployment is partially ready: {', '.join(degraded_features)}"
                    if partially_ready
                    else "Deployment readiness check failed. Check configuration and dependencies."
                )
            ),
        }
