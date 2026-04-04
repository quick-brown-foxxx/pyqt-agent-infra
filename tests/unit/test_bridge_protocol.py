"""Tests for bridge protocol types and JSON codec."""

import json

from qt_ai_dev_tools.bridge._protocol import (
    EvalRequest,
    EvalResponse,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
    socket_path_for_pid,
)


class TestEvalRequest:
    def test_defaults(self) -> None:
        req = EvalRequest(code="1+1")
        assert req.code == "1+1"
        assert req.mode == "auto"

    def test_explicit_mode(self) -> None:
        req = EvalRequest(code="x=1", mode="exec")
        assert req.mode == "exec"


class TestEvalResponse:
    def test_success(self) -> None:
        resp = EvalResponse(ok=True, result="2", type_name="int")
        assert resp.ok is True
        assert resp.result == "2"

    def test_error(self) -> None:
        resp = EvalResponse(ok=False, error="NameError: x", traceback_str="Traceback...")
        assert resp.ok is False
        assert resp.error == "NameError: x"

    def test_defaults(self) -> None:
        resp = EvalResponse(ok=True)
        assert resp.stdout == ""
        assert resp.duration_ms == 0
        assert resp.result is None


class TestCodec:
    def test_request_roundtrip(self) -> None:
        req = EvalRequest(code="print('hi')", mode="exec")
        encoded = encode_request(req)
        assert encoded.endswith(b"\n")
        decoded = decode_request(encoded)
        assert decoded.code == req.code
        assert decoded.mode == req.mode

    def test_response_roundtrip_success(self) -> None:
        resp = EvalResponse(ok=True, result="42", type_name="int", stdout="", duration_ms=3)
        encoded = encode_response(resp)
        assert encoded.endswith(b"\n")
        decoded = decode_response(encoded)
        assert decoded.ok == resp.ok
        assert decoded.result == resp.result
        assert decoded.type_name == resp.type_name
        assert decoded.duration_ms == resp.duration_ms

    def test_response_roundtrip_error(self) -> None:
        resp = EvalResponse(ok=False, error="SyntaxError", traceback_str="line 1")
        decoded = decode_response(encode_response(resp))
        assert decoded.ok is False
        assert decoded.error == "SyntaxError"
        assert decoded.traceback_str == "line 1"

    def test_request_unicode(self) -> None:
        req = EvalRequest(code='print("hello")')
        decoded = decode_request(encode_request(req))
        assert decoded.code == req.code

    def test_request_default_mode(self) -> None:
        """Decoding without explicit mode defaults to 'auto'."""
        data = json.dumps({"code": "1+1"}).encode()
        decoded = decode_request(data)
        assert decoded.mode == "auto"


class TestSocketPath:
    def test_socket_path_for_pid(self) -> None:
        path = socket_path_for_pid(1234)
        assert path == "/tmp/qt-ai-dev-tools-bridge-1234.sock"

    def test_socket_path_different_pids(self) -> None:
        assert socket_path_for_pid(1) != socket_path_for_pid(2)
