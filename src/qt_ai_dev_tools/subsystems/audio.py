"""PipeWire audio interaction for virtual mic, recording, and verification."""

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
from pathlib import Path

from qt_ai_dev_tools.subsystems._subprocess import check_tool, run_tool
from qt_ai_dev_tools.subsystems.models import (
    AudioSource,
    AudioStream,
    AudioVerification,
    VirtualMicInfo,
)

# Module-level storage for virtual mic process PID
_virtual_mic_pid: int | None = None
_PID_FILE = Path("/tmp/qt-ai-dev-tools-virtual-mic.pid")  # noqa: S108


def virtual_mic_start(node_name: str = "virtual-mic") -> VirtualMicInfo:
    """Start a PipeWire virtual microphone via pw-loopback.

    Creates a loopback node that appears as a microphone input,
    allowing audio files to be played into it.

    Args:
        node_name: Name for the virtual mic node.

    Returns:
        VirtualMicInfo with the process PID and node name.

    Raises:
        RuntimeError: If pw-loopback is not found or fails to start.
    """
    global _virtual_mic_pid
    check_tool("pw-loopback")

    process = subprocess.Popen(
        [
            "pw-loopback",
            f"--capture-props=media.class=Audio/Source,node.name={node_name}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    _virtual_mic_pid = process.pid
    _PID_FILE.write_text(str(process.pid))

    return VirtualMicInfo(pid=process.pid, node_name=node_name)


def virtual_mic_stop() -> None:
    """Stop the virtual microphone process.

    Kills the pw-loopback process started by virtual_mic_start().

    Raises:
        RuntimeError: If no virtual mic process is running.
    """
    global _virtual_mic_pid

    pid = _virtual_mic_pid
    if pid is None and _PID_FILE.exists():
        pid = int(_PID_FILE.read_text().strip())

    if pid is None:
        msg = "No virtual mic process found"
        raise RuntimeError(msg)

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError as exc:
        msg = f"Virtual mic process {pid} not found (already stopped?)"
        raise RuntimeError(msg) from exc
    finally:
        _virtual_mic_pid = None
        if _PID_FILE.exists():
            _PID_FILE.unlink()


def virtual_mic_play(path: Path, node_name: str = "virtual-mic") -> None:
    """Play an audio file into the virtual microphone.

    Uses pw-cat to play audio. If the file is not WAV, attempts
    conversion via ffmpeg first.

    Args:
        path: Path to the audio file.
        node_name: Target virtual mic node name.

    Raises:
        RuntimeError: If pw-cat/ffmpeg is not found or playback fails.
        FileNotFoundError: If the audio file does not exist.
    """
    if not path.exists():
        msg = f"Audio file not found: {path}"
        raise FileNotFoundError(msg)

    check_tool("pw-cat")

    play_path = path
    # Convert non-WAV files to WAV via ffmpeg
    if path.suffix.lower() not in (".wav", ".raw"):
        check_tool("ffmpeg")
        wav_path = path.with_suffix(".wav")
        run_tool(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-ar",
                "48000",
                "-ac",
                "1",
                str(wav_path),
            ]
        )
        play_path = wav_path

    run_tool(
        [
            "pw-cat",
            "--playback",
            f"--target={node_name}",
            str(play_path),
        ]
    )


def record(
    duration: float,
    output: Path,
    *,
    loopback: bool = False,
) -> Path:
    """Record audio from PipeWire.

    Args:
        duration: Recording duration in seconds.
        output: Output file path.
        loopback: If True, record from monitor/loopback source.

    Returns:
        Path to the recorded file.

    Raises:
        RuntimeError: If pw-record is not found or recording fails.
    """
    check_tool("pw-record")

    args = [
        "pw-record",
        "--rate=48000",
        "--channels=1",
    ]

    if loopback:
        args.append("--target=auto")

    args.append(str(output))

    # pw-record runs until interrupted; use timeout
    with contextlib.suppress(subprocess.TimeoutExpired):
        subprocess.run(
            args,
            timeout=duration + 0.5,
            capture_output=True,
            text=True,
        )

    return output


def sources() -> list[AudioSource]:
    """List PipeWire audio sources.

    Returns:
        List of AudioSource objects.

    Raises:
        RuntimeError: If pw-cli is not found or the query fails.
    """
    check_tool("pw-cli")
    output = run_tool(["pw-cli", "list-objects"])
    return _parse_sources(output)


def _parse_sources(output: str) -> list[AudioSource]:
    """Parse pw-cli list-objects output for audio sources.

    Args:
        output: Raw pw-cli output.

    Returns:
        Parsed list of AudioSource objects.
    """
    result: list[AudioSource] = []
    # Match blocks with type "PipeWire:Interface:Node"
    blocks = re.split(r"(?=id \d+,)", output)

    for block in blocks:
        if "Audio/Source" not in block:
            continue

        id_match = re.search(r"id (\d+),", block)
        name_match = re.search(r'node\.name\s*=\s*"([^"]*)"', block)
        desc_match = re.search(r'node\.description\s*=\s*"([^"]*)"', block)

        if id_match and name_match:
            source_id = int(id_match.group(1))
            name = name_match.group(1)
            description = desc_match.group(1) if desc_match else name

            result.append(
                AudioSource(
                    id=source_id,
                    name=name,
                    description=description,
                )
            )

    return result


def status() -> list[AudioStream]:
    """List active PipeWire audio streams.

    Returns:
        List of AudioStream objects.

    Raises:
        RuntimeError: If pw-cli is not found or the query fails.
    """
    check_tool("pw-cli")
    output = run_tool(["pw-cli", "list-objects"])
    return _parse_streams(output)


def _parse_streams(output: str) -> list[AudioStream]:
    """Parse pw-cli list-objects output for active streams.

    Args:
        output: Raw pw-cli output.

    Returns:
        Parsed list of AudioStream objects.
    """
    result: list[AudioStream] = []
    blocks = re.split(r"(?=id \d+,)", output)

    for block in blocks:
        if "PipeWire:Interface:Node" not in block:
            continue

        id_match = re.search(r"id (\d+),", block)
        name_match = re.search(r'node\.name\s*=\s*"([^"]*)"', block)
        state_match = re.search(r'state:\s*"?(\w+)"?', block)

        if id_match and name_match:
            stream_id = int(id_match.group(1))
            node_name = name_match.group(1)
            stream_state = state_match.group(1) if state_match else "unknown"

            result.append(
                AudioStream(
                    id=stream_id,
                    node_name=node_name,
                    state=stream_state,
                )
            )

    return result


def verify_not_silence(path: Path, threshold: float = 0.001) -> AudioVerification:
    """Verify an audio file is not silence using sox stat.

    sox outputs statistics to stderr, including maximum amplitude,
    RMS amplitude, and duration.

    Args:
        path: Path to the audio file.
        threshold: Minimum RMS amplitude to consider non-silent.

    Returns:
        AudioVerification with silence detection results.

    Raises:
        RuntimeError: If sox is not found.
        FileNotFoundError: If the audio file does not exist.
    """
    if not path.exists():
        msg = f"Audio file not found: {path}"
        raise FileNotFoundError(msg)

    check_tool("sox")

    # sox outputs stat info to stderr
    result = subprocess.run(
        ["sox", str(path), "-n", "stat"],
        capture_output=True,
        text=True,
    )

    return _parse_sox_stat(result.stderr, threshold)


def _parse_sox_stat(stderr: str, threshold: float) -> AudioVerification:
    """Parse sox stat stderr output.

    Expected format lines:
        Maximum amplitude:   0.123456
        RMS     amplitude:   0.012345
        Length (seconds):    5.000000

    Args:
        stderr: Raw sox stat stderr output.
        threshold: RMS amplitude threshold for silence detection.

    Returns:
        AudioVerification with parsed values.
    """
    max_amp = 0.0
    rms_amp = 0.0
    duration = 0.0

    max_match = re.search(r"Maximum amplitude:\s+([\d.eE+-]+)", stderr)
    if max_match:
        max_amp = float(max_match.group(1))

    rms_match = re.search(r"RMS\s+amplitude:\s+([\d.eE+-]+)", stderr)
    if rms_match:
        rms_amp = float(rms_match.group(1))

    dur_match = re.search(r"Length \(seconds\):\s+([\d.eE+-]+)", stderr)
    if dur_match:
        duration = float(dur_match.group(1))

    is_silent = rms_amp < threshold

    return AudioVerification(
        is_silent=is_silent,
        max_amplitude=max_amp,
        rms_amplitude=rms_amp,
        duration_seconds=duration,
    )
