from pathlib import Path


def test_deployment_artifacts_exist() -> None:
    for path in [
        Path("Dockerfile"),
        Path("requirements.txt"),
        Path(".gitignore"),
        Path("README.md"),
        Path("frontend/dashboard.html"),
        Path("frontend/static/dashboard.js"),
        Path("frontend/static/dashboard.css"),
        Path("frontend/static/api.js"),
    ]:
        assert path.exists(), f"missing {path}"


def test_dockerfile_targets_huggingface_spaces() -> None:
    contents = Path("Dockerfile").read_text()

    assert "python:3.11" in contents
    assert "uvicorn" in contents
    assert "7860" in contents


def test_readme_documents_demo_and_api_key() -> None:
    contents = Path("README.md").read_text()

    assert "OPENAI_API_KEY" in contents
    assert "python demo.py" in contents
    assert "SENTINEL" in contents
    assert "PRISM" in contents
    assert "FORGE" in contents
    assert "GUARDIAN" in contents
