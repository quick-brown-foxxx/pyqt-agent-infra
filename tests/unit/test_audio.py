"""Tests for audio subsystem."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestParseSoxStat:
    def test_parse_nonsilent_file(self) -> None:
        """_parse_sox_stat should detect non-silent audio."""
        from qt_ai_dev_tools.subsystems.audio import _parse_sox_stat

        stderr = (
            "Samples read:          48000\n"
            "Length (seconds):      1.000000\n"
            "Scaled by:         2147483647.0\n"
            "Maximum amplitude:   0.500000\n"
            "Minimum amplitude:  -0.500000\n"
            "Midline amplitude:   0.000000\n"
            "Mean    norm:         0.250000\n"
            "Mean    amplitude:    0.000000\n"
            "RMS     amplitude:   0.350000\n"
            "Maximum delta:       0.100000\n"
            "Minimum delta:       0.000000\n"
            "Mean    delta:        0.050000\n"
            "RMS     delta:        0.060000\n"
        )
        result = _parse_sox_stat(stderr, threshold=0.001)

        assert result.is_silent is False
        assert result.max_amplitude == pytest.approx(0.5)
        assert result.rms_amplitude == pytest.approx(0.35)
        assert result.duration_seconds == pytest.approx(1.0)

    def test_parse_silent_file(self) -> None:
        """_parse_sox_stat should detect silent audio."""
        from qt_ai_dev_tools.subsystems.audio import _parse_sox_stat

        stderr = "Length (seconds):      2.000000\nMaximum amplitude:   0.000100\nRMS     amplitude:   0.000050\n"
        result = _parse_sox_stat(stderr, threshold=0.001)

        assert result.is_silent is True
        assert result.max_amplitude == pytest.approx(0.0001)
        assert result.rms_amplitude == pytest.approx(0.00005)
        assert result.duration_seconds == pytest.approx(2.0)

    def test_parse_empty_output(self) -> None:
        """_parse_sox_stat should return zeros for empty output."""
        from qt_ai_dev_tools.subsystems.audio import _parse_sox_stat

        result = _parse_sox_stat("", threshold=0.001)

        assert result.is_silent is True
        assert result.max_amplitude == 0.0
        assert result.rms_amplitude == 0.0
        assert result.duration_seconds == 0.0


class TestVerifyNotSilence:
    def test_verify_raises_on_missing_file(self) -> None:
        """verify_not_silence should raise FileNotFoundError for missing file."""
        from qt_ai_dev_tools.subsystems.audio import verify_not_silence

        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            verify_not_silence(Path("/nonexistent/audio.wav"))

    def test_verify_calls_sox(self, tmp_path: Path) -> None:
        """verify_not_silence should call sox stat on the file."""
        from qt_ai_dev_tools.subsystems.audio import verify_not_silence

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav data")

        mock_result = type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "",
                "stderr": "Maximum amplitude:   0.5\nRMS     amplitude:   0.3\nLength (seconds):      1.0\n",
            },
        )()

        with (
            patch("qt_ai_dev_tools.subsystems.audio.check_tool"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_not_silence(audio_file)

            assert result.is_silent is False
            assert result.max_amplitude == pytest.approx(0.5)


class TestParseSources:
    def test_parse_audio_sources(self) -> None:
        """_parse_sources should extract Audio/Source entries."""
        from qt_ai_dev_tools.subsystems.audio import _parse_sources

        output = (
            "id 32, type PipeWire:Interface:Node/3\n"
            '    media.class = "Audio/Source"\n'
            '    node.name = "alsa_input.pci"\n'
            '    node.description = "Built-in Mic"\n'
            "id 45, type PipeWire:Interface:Node/3\n"
            '    media.class = "Audio/Sink"\n'
            '    node.name = "alsa_output.pci"\n'
        )
        sources = _parse_sources(output)

        assert len(sources) == 1
        assert sources[0].id == 32
        assert sources[0].name == "alsa_input.pci"
        assert sources[0].description == "Built-in Mic"

    def test_parse_no_sources(self) -> None:
        """_parse_sources should return empty list when no sources."""
        from qt_ai_dev_tools.subsystems.audio import _parse_sources

        sources = _parse_sources("")
        assert sources == []


class TestParseStreams:
    def test_parse_active_streams(self) -> None:
        """_parse_streams should extract Node entries."""
        from qt_ai_dev_tools.subsystems.audio import _parse_streams

        output = 'id 10, type PipeWire:Interface:Node/3\n    node.name = "firefox"\n    state: "running"\n'
        streams = _parse_streams(output)

        assert len(streams) == 1
        assert streams[0].id == 10
        assert streams[0].node_name == "firefox"
        assert streams[0].state == "running"


class TestVirtualMicStart:
    def test_start_returns_info(self) -> None:
        """virtual_mic_start should return VirtualMicInfo with PID."""
        from qt_ai_dev_tools.subsystems.audio import virtual_mic_start

        mock_process = type("Process", (), {"pid": 12345})()

        with (
            patch("qt_ai_dev_tools.subsystems.audio.check_tool"),
            patch("subprocess.Popen", return_value=mock_process),
            patch.object(Path, "write_text"),
        ):
            info = virtual_mic_start("test-mic")

            assert info.pid == 12345
            assert info.node_name == "test-mic"


class TestVirtualMicStop:
    def test_stop_raises_when_no_process(self) -> None:
        """virtual_mic_stop should raise RuntimeError when no process is tracked."""
        from qt_ai_dev_tools.subsystems import audio as audio_mod

        # Reset module state
        audio_mod._virtual_mic_pid = None

        with (
            patch.object(Path, "exists", return_value=False),
            pytest.raises(RuntimeError, match="No virtual mic process found"),
        ):
            audio_mod.virtual_mic_stop()
