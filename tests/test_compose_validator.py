import pytest

from server.services.compose_validator import ComposeValidator, ComposeValidationError


def test_validate_safe_compose():
    """Verify a safe Docker Compose file passes validation."""
    compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./data:/var/www/html:ro
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: testdb
    volumes:
      - ./dbdata:/var/lib/postgresql/data
"""
    # Should not raise
    ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_privileged_container():
    """Verify privileged mode is rejected."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    privileged: true
"""
    with pytest.raises(ComposeValidationError, match="privileged mode is not allowed"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_host_network():
    """Verify host networking is rejected."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    network_mode: host
"""
    with pytest.raises(ComposeValidationError, match="host networking is not allowed"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_dangerous_capabilities():
    """Verify dangerous capabilities are rejected."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    cap_add:
      - NET_ADMIN
"""
    with pytest.raises(ComposeValidationError, match="not allowed"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_system_bind_mounts():
    """Verify bind mounts to system directories are rejected."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    volumes:
      - /etc/passwd:/app/config:ro
"""
    with pytest.raises(ComposeValidationError, match="bind mount"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_root_bind_mount():
    """Verify bind mounts to root are rejected."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    volumes:
      - /:/container_root
"""
    with pytest.raises(ComposeValidationError, match="bind mount"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_allows_relative_volume_mounts():
    """Verify relative path volume mounts are allowed."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    volumes:
      - ./workspace:/app/workspace
      - data:/app/data
"""
    # Should not raise
    ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_invalid_yaml():
    """Verify invalid YAML is rejected."""
    compose = """
version: '3.8'
services:
  app
    image: nginx  # Missing colon
"""
    with pytest.raises(ComposeValidationError, match="Invalid YAML"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_non_object_config():
    """Verify non-object top-level config is rejected."""
    compose = "- not a mapping"
    with pytest.raises(ComposeValidationError, match="must be a YAML object"):
        ComposeValidator.validate_compose_content(compose)


def test_validate_rejects_ipc_mode():
    """Verify dangerous IPC modes are rejected."""
    compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    ipc: host
"""
    with pytest.raises(ComposeValidationError, match="not allowed"):
        ComposeValidator.validate_compose_content(compose)
