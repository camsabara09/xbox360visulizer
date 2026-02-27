"""Signal analysis module using FFT and beat detection."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass
class AnalysisState:
    bass: float
    mid: float
    high: float
    volume: float
    beat: bool
    treble_hit: bool
    spectrum: np.ndarray


class AudioAnalyzer:
    def __init__(self, samplerate: int, blocksize: int):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.window = np.hanning(blocksize).astype(np.float32)
        self.freqs = np.fft.rfftfreq(blocksize, 1.0 / samplerate)

        self.bass_hist: deque[float] = deque(maxlen=64)
        self.high_hist: deque[float] = deque(maxlen=64)
        self.vol_hist: deque[float] = deque(maxlen=64)

    def _band_energy(self, mag: np.ndarray, low: float, high: float) -> float:
        mask = (self.freqs >= low) & (self.freqs < high)
        if not np.any(mask):
            return 0.0
        return float(np.mean(mag[mask]))

    def analyze(self, frame: np.ndarray) -> AnalysisState:
        frame = np.nan_to_num(frame, copy=False)
        frame = frame[: self.blocksize]
        if frame.shape[0] < self.blocksize:
            frame = np.pad(frame, (0, self.blocksize - frame.shape[0]))

        windowed = frame * self.window
        spectrum = np.fft.rfft(windowed)
        mag = np.abs(spectrum).astype(np.float32)

        bass = self._band_energy(mag, 20, 180)
        mid = self._band_energy(mag, 180, 2000)
        high = self._band_energy(mag, 2000, 12000)
        volume = float(np.sqrt(np.mean(frame**2)))

        self.bass_hist.append(bass)
        self.high_hist.append(high)
        self.vol_hist.append(volume)

        bass_avg = np.mean(self.bass_hist) if self.bass_hist else bass
        high_avg = np.mean(self.high_hist) if self.high_hist else high

        beat = bass > (bass_avg * 1.55 + 1e-6)
        treble_hit = high > (high_avg * 1.65 + 1e-6)

        norm = np.max(mag) + 1e-6
        mag_norm = mag / norm

        return AnalysisState(
            bass=float(bass),
            mid=float(mid),
            high=float(high),
            volume=float(volume),
            beat=bool(beat),
            treble_hit=bool(treble_hit),
            spectrum=mag_norm,
        )
