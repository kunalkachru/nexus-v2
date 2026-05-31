from __future__ import annotations

from fastapi import HTTPException, Request


OPENAI_KEY_HEADER = "x-openai-api-key"


def extract_request_openai_api_key(request: Request) -> str | None:
    raw = str(request.headers.get(OPENAI_KEY_HEADER, "")).strip()
    if not raw:
        return None
    if not raw.startswith("sk-") or len(raw) < 12:
        raise HTTPException(status_code=400, detail="invalid OpenAI API key format")
    return raw


def build_llm_access(
    *,
    live_reasoning_requested: bool,
    user_key_provided: bool,
    server_key_available: bool,
    live_reasoning_active: bool,
) -> dict[str, object]:
    if live_reasoning_active:
        key_source = "user" if user_key_provided else "server"
        return {
            "mode": "live",
            "key_source": key_source,
            "user_key_provided": user_key_provided,
            "server_key_available": server_key_available,
            "live_reasoning_requested": live_reasoning_requested,
            "message": (
                "Live reasoning is active with your request-scoped OpenAI key."
                if user_key_provided
                else "Live reasoning is active with the server OpenAI key."
            ),
        }

    if live_reasoning_requested and not (user_key_provided or server_key_available):
        message = "Deterministic mode is active. Add your OpenAI key to enable live reasoning."
    elif live_reasoning_requested and user_key_provided:
        message = "Deterministic mode is active because the live reasoning request could not be completed."
    else:
        message = "Deterministic mode is active. No OpenAI key is being used."

    return {
        "mode": "deterministic",
        "key_source": "user" if user_key_provided else "none",
        "user_key_provided": user_key_provided,
        "server_key_available": server_key_available,
        "live_reasoning_requested": live_reasoning_requested,
        "message": message,
    }
