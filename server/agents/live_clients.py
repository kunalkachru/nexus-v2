from __future__ import annotations

import json
import logging
import os


logger = logging.getLogger(__name__)


class OpenAIForgeClient:
    """Optional live OpenAI backend for FORGE."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "forge_runbook",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "language": {"type": "string"},
                            "summary": {"type": "string"},
                            "code": {"type": "string"},
                            "estimated_cost_usd": {"type": "number"},
                        },
                        "required": ["language", "summary", "code", "estimated_cost_usd"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        try:
            data = json.loads(response.output_text)
            required_fields = ["language", "summary", "code", "estimated_cost_usd"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.exception(f"Invalid FORGE response format: {e}")
            raise ValueError(f"FORGE client returned invalid JSON or missing fields: {e}") from e


class OpenAISentinelClient:
    """Optional live OpenAI backend for SENTINEL classification."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "sentinel_classification",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "incident_id": {"type": "string"},
                            "incident_name": {"type": "string"},
                            "severity": {"type": "string"},
                            "confidence": {"type": "number"},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["incident_id", "incident_name", "severity", "confidence", "reasoning"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        try:
            data = json.loads(response.output_text)
            required_fields = ["incident_id", "incident_name", "severity", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.exception(f"Invalid SENTINEL response format: {e}")
            raise ValueError(f"SENTINEL client returned invalid JSON or missing fields: {e}") from e


class OpenAIPrismClient:
    """Optional live OpenAI backend for PRISM diagnosis synthesis."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "prism_diagnosis",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "root_cause": {"type": "string"},
                            "confidence": {"type": "number"},
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "queried_sources": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "reasoning": {"type": "string"},
                        },
                        "required": ["root_cause", "confidence", "evidence", "queried_sources", "reasoning"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        try:
            data = json.loads(response.output_text)
            required_fields = ["root_cause", "confidence", "evidence", "queried_sources", "reasoning"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.exception(f"Invalid PRISM response format: {e}")
            raise ValueError(f"PRISM client returned invalid JSON or missing fields: {e}") from e
