"""Audio file playback via sounddevice with analyzer tap-out blocks."""

from __future__ import annotations

import os
import queue
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


@dataclass
class PlaybackInfo:
    filename: str
    position_seconds: float
    duration_seconds: float
    playing: bool
    loaded: bool


class AudioFilePlayer:
    def __init__(self, blocksize: int = 1024):
        self.blocksize = blocksize
        self._audio: Optional[np.ndarray] = None
        self._samplerate: int = 44100
        self._channels: int = 0
        self._position: int = 0
        self._playing: bool = False
        self._loaded_path: Optional[str] = None

        self._stream: Optional[sd.OutputStream] = None
        self._lock = threading.Lock()
        self._analysis_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=8)

    @property
    def samplerate(self) -> int:
        return self._samplerate

    @property
    def loaded(self) -> bool:
        return self._audio is not None

    def load(self, path: str):
        data, samplerate = sf.read(path, dtype="float32", always_2d=True)
        with self._lock:
            self._audio = data
            self._samplerate = int(samplerate)
            self._channels = data.shape[1]
            self._position = 0
            self._playing = False
            self._loaded_path = path

        self._restart_stream()

    def _restart_stream(self):
        self.close()
        if not self.loaded:
            return
        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            blocksize=self.blocksize,
            channels=self._channels,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        outdata.fill(0)
        with self._lock:
            if self._audio is None or not self._playing:
                block = np.zeros((frames, 1), dtype=np.float32)
            else:
                start = self._position
                end = min(start + frames, self._audio.shape[0])
                chunk = self._audio[start:end]
                wrote = end - start
                outdata[:wrote] = chunk
                if wrote < frames:
                    outdata[wrote:] = 0
                    self._playing = False
                self._position = end
                block = outdata[:frames].copy()

        mono = np.mean(block, axis=1).astype(np.float32)
        try:
            self._analysis_queue.put_nowait(mono)
        except queue.Full:
            try:
                self._analysis_queue.get_nowait()
            except queue.Empty:
                pass
            self._analysis_queue.put_nowait(mono)

    def play(self):
        with self._lock:
            if self._audio is None:
                return
            self._playing = True

    def pause(self):
        with self._lock:
            self._playing = False

    def toggle(self):
        with self._lock:
            if self._audio is None:
                return
            self._playing = not self._playing

    def restart(self):
        with self._lock:
            if self._audio is None:
                return
            self._position = 0

    def seek(self, seconds: float):
        with self._lock:
            if self._audio is None:
                return
            delta = int(seconds * self._samplerate)
            max_pos = self._audio.shape[0] - 1
            self._position = max(0, min(max_pos, self._position + delta))

    def get_last_block(self) -> np.ndarray:
        latest = None
        while True:
            try:
                latest = self._analysis_queue.get_nowait()
            except queue.Empty:
                break
        if latest is None:
            return np.zeros(self.blocksize, dtype=np.float32)
        return latest

    def get_info(self) -> PlaybackInfo:
        with self._lock:
            if self._audio is None:
                return PlaybackInfo(filename="", position_seconds=0.0, duration_seconds=0.0, playing=False, loaded=False)
            duration = self._audio.shape[0] / self._samplerate
            pos = self._position / self._samplerate
            filename = os.path.basename(self._loaded_path or "")
            return PlaybackInfo(
                filename=filename,
                position_seconds=float(pos),
                duration_seconds=float(duration),
                playing=self._playing,
                loaded=True,
            )

    def close(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
