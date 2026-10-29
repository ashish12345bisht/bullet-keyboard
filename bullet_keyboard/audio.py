"""Low-latency polyphonic mixers: PipeWire's pw-play on Linux, sounddevice elsewhere."""

import subprocess
import threading

import numpy as np

from .sounds import SR

BLOCK = 256  # frames per write (~5 ms)
MAX_VOICES = 24
F_SETPIPE_SZ = 1031


class _Voices:
    """Overlapping one-shot sounds, summed and soft-clipped into int16 blocks."""

    def __init__(self, volume):
        self.volume = volume
        self._voices = []  # [array, position]
        self._lock = threading.Lock()

    def play(self, samples):
        with self._lock:
            if len(self._voices) >= MAX_VOICES:
                self._voices.pop(0)
            self._voices.append([samples, 0])

    def _mix(self, frames):
        out = np.zeros(frames, dtype=np.float32)
        with self._lock:
            alive = []
            for v in self._voices:
                s, pos = v
                chunk = s[pos:pos + frames]
                out[:chunk.size] += chunk
                v[1] = pos + frames
                if v[1] < s.size:
                    alive.append(v)
            self._voices = alive
        return (np.tanh(out * self.volume) * 32767).astype("<i2")


class Mixer(_Voices):
    """Streams raw PCM into pw-play (Linux / PipeWire)."""

    def __init__(self, volume=0.7):
        super().__init__(volume)
        self._running = True
        self._proc = subprocess.Popen(
            ["pw-play", "--raw", "--format", "s16", "--rate", str(SR), "--channels", "1",
             "--latency", f"{BLOCK}/{SR}", "-"],
            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        # Shrink the pipe so we can't queue up more than a few ms of audio ahead of playback.
        try:
            import fcntl
            fcntl.fcntl(self._proc.stdin.fileno(), F_SETPIPE_SZ, 4096)
        except OSError:
            pass
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            pcm = self._mix(BLOCK)
            try:
                self._proc.stdin.write(pcm.tobytes())
                self._proc.stdin.flush()
            except (BrokenPipeError, ValueError):
                break

    def close(self):
        self._running = False
        self._thread.join(timeout=1)
        try:
            self._proc.stdin.close()
        except OSError:
            pass
        self._proc.terminate()


class StreamMixer(_Voices):
    """Plays through the default output device via PortAudio (Windows / macOS)."""

    def __init__(self, volume=0.7):
        import sounddevice as sd

        super().__init__(volume)
        self._stream = sd.OutputStream(
            samplerate=SR, channels=1, dtype="int16", blocksize=BLOCK,
            latency="low", callback=self._callback,
        )
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        outdata[:, 0] = self._mix(frames)

    def close(self):
        self._stream.stop()
        self._stream.close()
