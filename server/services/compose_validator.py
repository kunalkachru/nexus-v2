"""Validate user-provided Docker Compose files for safety."""

import yaml
from pathlib import Path


class ComposeValidationError(Exception):
    """Raised when a Docker Compose file fails validation."""
    pass


class ComposeValidator:
    """Validates Docker Compose files for safe execution."""

    FORBIDDEN_SERVICE_KEYS = {
        "privileged",
        "cap_add",
        "cap_drop",
        "devices",
        "cgroup",
        "ipc",
    }

    FORBIDDEN_VOLUME_PATTERNS = [
        "/",
        "/root",
        "/home",
        "/var",
        "/etc",
        "/usr",
        "/bin",
        "/sbin",
    ]

    @staticmethod
    def validate_compose_content(compose_yaml: str) -> None:
        """
        Validate Docker Compose YAML content for safety.

        Checks for:
        - privileged containers
        - host networking
        - bind mounts outside sandbox
        - dangerous capabilities

        Raises ComposeValidationError if validation fails.
        """
        try:
            config = yaml.safe_load(compose_yaml)
        except yaml.YAMLError as e:
            raise ComposeValidationError(f"Invalid YAML: {e}")

        if not isinstance(config, dict):
            raise ComposeValidationError("Compose config must be a YAML object")

        services = config.get("services", {})
        if not isinstance(services, dict):
            raise ComposeValidationError("'services' must be a mapping")

        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue

            # Check for privileged mode
            if service_config.get("privileged"):
                raise ComposeValidationError(
                    f"Service '{service_name}': privileged mode is not allowed"
                )

            # Check for dangerous keys
            for forbidden_key in ComposeValidator.FORBIDDEN_SERVICE_KEYS:
                if forbidden_key in service_config:
                    raise ComposeValidationError(
                        f"Service '{service_name}': '{forbidden_key}' is not allowed"
                    )

            # Check for dangerous networking
            if service_config.get("network_mode") in ("host", "privileged"):
                raise ComposeValidationError(
                    f"Service '{service_name}': host networking is not allowed"
                )

            # Check volumes for dangerous bind mounts
            volumes = service_config.get("volumes", [])
            if isinstance(volumes, list):
                for volume in volumes:
                    if isinstance(volume, str):
                        ComposeValidator._check_volume_mount(volume, service_name)
                    elif isinstance(volume, dict):
                        host_path = volume.get("source")
                        if host_path:
                            ComposeValidator._check_volume_mount(host_path, service_name)

    @staticmethod
    def _check_volume_mount(volume_spec: str, service_name: str) -> None:
        """Check if a volume mount is safe."""
        if ":" not in volume_spec:
            return

        host_path = volume_spec.split(":")[0]

        # Reject absolute paths outside sandbox
        if host_path.startswith("/"):
            for forbidden in ComposeValidator.FORBIDDEN_VOLUME_PATTERNS:
                if host_path == forbidden or host_path.startswith(forbidden + "/"):
                    raise ComposeValidationError(
                        f"Service '{service_name}': bind mount to '{host_path}' is not allowed"
                    )

    @staticmethod
    def validate_compose_file(path: Path) -> None:
        """Validate a Docker Compose file on disk."""
        if not path.exists():
            raise ComposeValidationError(f"File not found: {path}")

        if not path.is_file():
            raise ComposeValidationError(f"Not a file: {path}")

        try:
            with open(path) as f:
                content = f.read()
            ComposeValidator.validate_compose_content(content)
        except ComposeValidationError:
            raise
        except Exception as e:
            raise ComposeValidationError(f"Failed to read file: {e}")
