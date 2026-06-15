from pathlib import Path


def test_deployment_artifacts_exist() -> None:
    for path in [
        Path("Dockerfile"),
        Path("Dockerfile.runtime-host"),
        Path("docker-compose.yml"),
        Path("requirements.txt"),
        Path(".gitignore"),
        Path("README.md"),
        Path("docs/internal/OPERATIONS.md"),
        Path("docs/internal/OPERATOR_RUNBOOK.md"),
        Path("docs/internal/README.md"),
        Path("frontend/dashboard.html"),
        Path("frontend/queue.html"),
        Path("frontend/incident.html"),
        Path("frontend/history.html"),
        Path("frontend/inputs.html"),
        Path("frontend/replay.html"),
        Path("frontend/training.html"),
        Path("frontend/settings.html"),
        Path("frontend/static/dashboard.js"),
        Path("frontend/static/incident.js"),
        Path("frontend/static/inputs.js"),
        Path("frontend/static/training.js"),
        Path("frontend/static/dashboard.css"),
        Path("frontend/static/api.js"),
        Path("ops/kubernetes/deployment.yaml"),
        Path("ops/kubernetes/configmap.yaml"),
    ]:
        assert path.exists(), f"missing {path}"


def test_dockerfile_targets_huggingface_spaces() -> None:
    contents = Path("Dockerfile").read_text()

    assert "ARG APP_ENV=demo" in contents
    assert "ENV APP_ENV=${APP_ENV}" in contents
    assert "python:3.11" in contents
    assert "uvicorn" in contents
    assert "7860" in contents


def test_runtime_host_deployment_artifacts_exist() -> None:
    compose = Path("docker-compose.yml").read_text()
    runtime_host_dockerfile = Path("Dockerfile.runtime-host").read_text()
    script = Path("scripts/docker_fresh.sh").read_text()

    assert "runtime-host:" in compose
    assert "Dockerfile.runtime-host" in compose
    assert "NEXUS_RUNTIME_HOST_BASE_URL" in compose
    assert "NEXUS_RUNTIME_HOST_SHARED_TOKEN" in compose
    assert "NEXUS_RUNTIME_HOST_SOURCE_PATH" in compose
    assert "NEXUS_REPLICA_PACKS_ROOT" in compose
    assert "NEXUS_RUNTIME_HTTP_HOST" in compose
    assert "docker compose --profile runtime-host" in script or "COMPOSE_PROFILES" in script
    assert "NEXUS_RUNTIME_HOST_SOURCE_PATH" in script
    assert "NEXUS_RUNTIME_HTTP_HOST" in script
    assert "docker.io" in runtime_host_dockerfile or "docker-compose" in runtime_host_dockerfile


def test_readme_documents_demo_and_api_key() -> None:
    contents = Path("README.md").read_text()

    assert "OPENAI_API_KEY" in contents
    assert "python demo.py" in contents
    assert "SENTINEL" in contents
    assert "PRISM" in contents
    assert "FORGE" in contents
    assert "GUARDIAN" in contents
