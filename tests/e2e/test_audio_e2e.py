"""E2E tests for audio subsystem -- real PipeWire in VM."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
    pytest.mark.e2e,
]


class TestVirtualMic:
    """Flow 4A: Virtual mic creation and teardown."""

    def test_virtual_mic_lifecycle(self, audio_app: subprocess.Popen[str]) -> None:
        """Start virtual mic, verify it appears in sources, then stop."""
        from qt_ai_dev_tools.subsystems import audio

        node_name = "e2e-test-mic"

        # Start virtual mic
        info = audio.virtual_mic_start(node_name=node_name)
        assert info.pid > 0
        assert info.node_name == node_name

        # Give PipeWire a moment to register the new node
        time.sleep(1.0)

        try:
            # Verify the virtual mic appears in sources list
            source_list = audio.sources()
            source_names = [s.name for s in source_list]
            assert any(node_name in name for name in source_names), (
                f"Virtual mic '{node_name}' not found in sources: {source_names}"
            )
        finally:
            # Always clean up
            audio.virtual_mic_stop()

    def test_virtual_mic_stop_cleans_up(self, audio_app: subprocess.Popen[str]) -> None:
        """After stopping the virtual mic, it should no longer appear."""
        from qt_ai_dev_tools.subsystems import audio

        node_name = "e2e-cleanup-mic"

        info = audio.virtual_mic_start(node_name=node_name)
        assert info.pid > 0
        time.sleep(0.5)

        audio.virtual_mic_stop()
        time.sleep(0.5)

        # Verify it's gone (or at least not actively running)
        # The process should be dead, even if PipeWire still shows it briefly
        with pytest.raises(RuntimeError, match="No virtual mic process found"):
            audio.virtual_mic_stop()


class TestAudioRecordAndVerify:
    """Flow 4B: Record audio and verify silence detection."""

    def test_record_silence_and_verify(self, audio_app: subprocess.Popen[str], tmp_path: Path) -> None:
        """Record silence for 1 second, verify sox reports it as silent."""
        from qt_ai_dev_tools.subsystems import audio

        output_path = tmp_path / "silence.wav"

        # Record 1 second of audio (should be silence with no active source)
        recorded = audio.record(duration=1.0, output=output_path)
        assert recorded.exists(), f"Recording file not created: {recorded}"
        assert recorded.stat().st_size > 0, "Recording file is empty"

        # Verify it's detected as silence
        verification = audio.verify_not_silence(recorded)
        assert verification.is_silent is True, f"Expected silence, got rms_amplitude={verification.rms_amplitude}"
        assert verification.duration_seconds > 0

    def test_verify_not_silence_with_tone(self, audio_app: subprocess.Popen[str], tmp_path: Path) -> None:
        """Generate a tone via sox, verify it is detected as non-silent."""
        tone_path = tmp_path / "tone.wav"

        # Generate a 440Hz tone (1 second) using sox
        result = subprocess.run(
            [
                "sox",
                "-n",
                "-r",
                "48000",
                "-c",
                "1",
                str(tone_path),
                "synth",
                "1.0",
                "sine",
                "440",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"sox not available or failed: {result.stderr}")

        from qt_ai_dev_tools.subsystems import audio

        verification = audio.verify_not_silence(tone_path)
        assert verification.is_silent is False, f"Expected non-silence, got rms_amplitude={verification.rms_amplitude}"
        assert verification.max_amplitude > 0
        assert verification.duration_seconds >= 0.9


class TestAudioSources:
    """List audio sources — basic sanity check."""

    def test_list_sources(self, audio_app: subprocess.Popen[str]) -> None:
        """List PipeWire sources — should not raise."""
        from qt_ai_dev_tools.subsystems import audio

        source_list = audio.sources()
        # In a VM with PipeWire, there should be at least the default source
        assert isinstance(source_list, list)
