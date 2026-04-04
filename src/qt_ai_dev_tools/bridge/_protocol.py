"""Bridge protocol: request/response types and JSON codec."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Final


@dataclass(slots=True)
class EvalRequest:
    """Code execution request sent from CLI to bridge server."""

    code: str
    mode: str = "auto"  # "auto" | "eval" | "exec"


@dataclass(slots=True)
class EvalResponse:
    """Code execution response sent from bridge server to CLI."""

    ok: bool
    result: str | None = None
    type_name: str | None = None
    stdout: str = ""
    error: str | None = None
    traceback_str: str | None = None
    duration_ms: int = 0


def _loads_dict(data: bytes) -> dict[str, object]:
    """Parse JSON bytes as a string-keyed dict (typed boundary for json.loads).

    json.loads always produces str keys for JSON objects, so the cast is safe
    when we verify the top-level value is a dict.
    """
    raw: dict[str, object] = json.loads(data)  # type: ignore[reportAny]  # rationale: json.loads returns Any; JSON objects always have str keys
    if not isinstance(raw, dict):
        msg = f"Expected JSON object, got {type(raw).__name__}"
        raise TypeError(msg)
    return raw


def encode_request(req: EvalRequest) -> bytes:
    """Encode request as newline-terminated JSON bytes."""
    return json.dumps(asdict(req), ensure_ascii=False).encode() + b"\n"


def decode_request(data: bytes) -> EvalRequest:
    """Decode request from JSON bytes."""
    d = _loads_dict(data)
    code = d["code"]
    if not isinstance(code, str):
        msg = f"Expected 'code' to be str, got {type(code).__name__}"
        raise TypeError(msg)
    mode = d.get("mode", "auto")
    if not isinstance(mode, str):
        msg = f"Expected 'mode' to be str, got {type(mode).__name__}"
        raise TypeError(msg)
    return EvalRequest(code=code, mode=mode)


def encode_response(resp: EvalResponse) -> bytes:
    """Encode response as newline-terminated JSON bytes."""
    return json.dumps(asdict(resp), ensure_ascii=False).encode() + b"\n"


def _get_optional_str(d: dict[str, object], key: str) -> str | None:
    """Extract an optional string field from a decoded JSON dict."""
    val = d.get(key)
    if val is None:
        return None
    if not isinstance(val, str):
        msg = f"Expected '{key}' to be str or null, got {type(val).__name__}"
        raise TypeError(msg)
    return val


def decode_response(data: bytes) -> EvalResponse:
    """Decode response from JSON bytes."""
    d = _loads_dict(data)
    ok_val = d["ok"]
    if not isinstance(ok_val, bool):
        msg = f"Expected 'ok' to be bool, got {type(ok_val).__name__}"
        raise TypeError(msg)
    stdout_val = d.get("stdout", "")
    if not isinstance(stdout_val, str):
        msg = f"Expected 'stdout' to be str, got {type(stdout_val).__name__}"
        raise TypeError(msg)
    duration_val = d.get("duration_ms", 0)
    if not isinstance(duration_val, int) or isinstance(duration_val, bool):
        msg = f"Expected 'duration_ms' to be int, got {type(duration_val).__name__}"
        raise TypeError(msg)
    return EvalResponse(
        ok=ok_val,
        result=_get_optional_str(d, "result"),
        type_name=_get_optional_str(d, "type_name"),
        stdout=stdout_val,
        error=_get_optional_str(d, "error"),
        traceback_str=_get_optional_str(d, "traceback_str"),
        duration_ms=duration_val,
    )


# Socket path convention
SOCKET_PATH_PATTERN: Final = "/tmp/qt-ai-dev-tools-bridge-{pid}.sock"  # noqa: S108


def socket_path_for_pid(pid: int) -> str:
    """Return the expected socket path for a given PID."""
    return SOCKET_PATH_PATTERN.format(pid=pid)
