"""Bridge eval engine: execute Python code with stdout capture."""

from __future__ import annotations

import contextlib
import io
import time
import traceback as tb_module

from qt_ai_dev_tools.bridge._protocol import EvalMode, EvalResponse
from qt_ai_dev_tools.bridge._qt_namespace import build_qt_namespace

MAX_RESULT_BYTES: int = 65536  # 64KB

# Re-export for convenience
__all__ = ["MAX_RESULT_BYTES", "build_qt_namespace", "execute"]


def _truncate_repr(value: object) -> tuple[str, str]:
    """Return (repr_string, type_name) with truncation if needed."""
    type_name = type(value).__name__
    full = repr(value)
    if len(full) <= MAX_RESULT_BYTES:
        return full, type_name
    total_kb = len(full) // 1024
    return full[:MAX_RESULT_BYTES] + f"\n[truncated, {total_kb}kB total]", type_name


def execute(code: str, namespace: dict[str, object], mode: EvalMode = "auto") -> EvalResponse:
    """Execute Python code and return a structured response.

    Modes:
        auto: try eval (expression), fall back to exec (statement) on SyntaxError
        eval: expression only, error if not an expression
        exec: statement only, result is always None
    """
    start_ns = time.perf_counter_ns()
    try:
        if mode == "eval":
            return _do_eval(code, namespace, start_ns)
        if mode == "exec":
            return _do_exec(code, namespace, start_ns)
        # auto: try eval, fall back to exec
        try:
            return _do_eval(code, namespace, start_ns)
        except SyntaxError:
            return _do_exec(code, namespace, start_ns)
    except Exception as exc:
        duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
        return EvalResponse(
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            traceback_str=tb_module.format_exc(),
            duration_ms=duration_ms,
        )


def _do_eval(code: str, namespace: dict[str, object], start_ns: int) -> EvalResponse:
    """Evaluate an expression and return its repr.

    Captures stdout so that expressions like ``print('hello')`` have their
    output included in the response.
    """
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture):
        result: object = eval(code, namespace)  # noqa: S307  # type: ignore[reportAny]  # rationale: eval() inherently returns Any — this is the dynamic eval boundary
    duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
    result_str, type_name = _truncate_repr(result)
    # Update REPL-style _ variable
    namespace["_"] = result
    return EvalResponse(
        ok=True, result=result_str, type_name=type_name, stdout=stdout_capture.getvalue(), duration_ms=duration_ms
    )


def _do_exec(code: str, namespace: dict[str, object], start_ns: int) -> EvalResponse:
    """Execute statements, capturing stdout."""
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture):
        exec(code, namespace)  # noqa: S102
    duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
    stdout_str = stdout_capture.getvalue()
    return EvalResponse(ok=True, result=None, type_name="NoneType", stdout=stdout_str, duration_ms=duration_ms)
