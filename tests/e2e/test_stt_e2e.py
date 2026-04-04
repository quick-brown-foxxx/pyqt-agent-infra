"""E2E tests for STT (speech-to-text) workflow -- fake STT app in VM."""

from __future__ import annotations

import os
import subprocess
import time

import pytest

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
    pytest.mark.e2e,
]


class TestSttWorkflow:
    """Test the record → transcribe → read result workflow."""

    def test_record_and_transcribe(self, stt_app: subprocess.Popen[str]) -> None:
        """Click Record, then Transcribe, verify result text appears."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None, "No bridge socket found"

        # Click "Record Audio" button
        eval_code(sock, "widgets['record_btn'].click()")
        time.sleep(0.5)

        # Verify status updated
        resp = eval_code(sock, "widgets['status_label'].text()")
        assert resp.ok is True
        assert resp.result is not None
        assert "captured" in resp.result.lower() or "Recording" in resp.result

        # Click "Transcribe" button
        eval_code(sock, "widgets['transcribe_btn'].click()")
        time.sleep(0.5)

        # Verify transcription result
        resp = eval_code(sock, "widgets['result_text'].toPlainText()")
        assert resp.ok is True
        assert resp.result is not None
        # The fake STT app returns a hardcoded sentence
        assert "quick brown fox" in resp.result.lower()

        # Verify status label
        resp = eval_code(sock, "widgets['status_label'].text()")
        assert resp.ok is True
        assert resp.result is not None
        assert "complete" in resp.result.lower()

    def test_transcribe_without_recording(self, stt_app: subprocess.Popen[str]) -> None:
        """Transcribe without recording first — should show error state."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None, "No bridge socket found"

        # Reset the app state: clear the recording flag via bridge
        eval_code(sock, "widgets['SttTestWindow']._has_recording = False")
        eval_code(sock, "widgets['result_text'].clear()")

        # Click "Transcribe" without recording first
        eval_code(sock, "widgets['transcribe_btn'].click()")
        time.sleep(0.3)

        # Verify the app reports no recording
        resp = eval_code(sock, "widgets['status_label'].text()")
        assert resp.ok is True
        assert resp.result is not None
        assert "no recording" in resp.result.lower()

        # Verify result text is still empty
        resp = eval_code(sock, "widgets['result_text'].toPlainText()")
        assert resp.ok is True
        # Result should be empty string (repr'd as '')
        assert resp.result in ("''", "")


class TestSttWithAudioSubsystem:
    """Integration: use audio subsystem to feed into STT app."""

    def test_virtual_mic_and_stt(self, stt_app: subprocess.Popen[str]) -> None:
        """Start virtual mic, record in app, transcribe — full pipeline."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.subsystems import audio

        sock = find_bridge_socket()
        assert sock is not None, "No bridge socket found"

        node_name = "stt-e2e-mic"

        # Start virtual mic (simulates audio input being available)
        info = audio.virtual_mic_start(node_name=node_name)
        assert info.pid > 0
        time.sleep(0.5)

        try:
            # Click record in the app
            eval_code(sock, "widgets['record_btn'].click()")
            time.sleep(0.5)

            # Click transcribe
            eval_code(sock, "widgets['transcribe_btn'].click()")
            time.sleep(0.5)

            # Verify transcription appeared
            resp = eval_code(sock, "widgets['result_text'].toPlainText()")
            assert resp.ok is True
            assert resp.result is not None
            assert "quick brown fox" in resp.result.lower()
        finally:
            audio.virtual_mic_stop()
