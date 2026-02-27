"""Audio capture module for real-time visualization."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd


@dataclass
class AudioConfig:
    samplerate: int = 44100
    blocksize: int = 1024
    channels: int = 1
    device: Optional[int] = None


class AudioInput:
    """Continuously captures live audio and exposes the latest frame."""

    def __init__(self, config: AudioConfig | None = None):
        self.config = config or AudioConfig()
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=8)
        self._stream: sd.InputStream | None = None
        self._running = threading.Event()

    def _audio_callback(self, indata, frames, time, status):
        if status:
            return
        mono = np.mean(indata, axis=1).astype(np.float32)
        try:
            self._queue.put_nowait(mono)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put_nowait(mono)

    def start(self):
        if self._running.is_set():
            return
        self._stream = sd.InputStream(
            samplerate=self.config.samplerate,
            blocksize=self.config.blocksize,
            channels=self.config.channels,
            device=self.config.device,
            callback=self._audio_callback,
            dtype="float32",
        )
        self._stream.start()
        self._running.set()

    def stop(self):
        self._running.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_latest_frame(self) -> np.ndarray:
        """Get most recent audio frame, or silence if no frame is ready."""
        latest = None
        while True:
            try:
                latest = self._queue.get_nowait()
            except queue.Empty:
                break

        if latest is None:
            return np.zeros(self.config.blocksize, dtype=np.float32)
        return latest
