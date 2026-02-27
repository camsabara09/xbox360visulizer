# Xbox 360 Rage Visualizer (Python)

A real-time, psychedelic music visualizer inspired by the classic Xbox 360 CD visualizer, but tuned for modern high-energy music.

## Features

- Live audio input capture with **sounddevice**.
- Real-time **NumPy FFT** frequency analysis.
- Split frequency bands into:
  - Bass (20-180 Hz)
  - Mid (180-2000 Hz)
  - High (2000-12000 Hz)
- Beat detection from bass energy spikes.
- Treble/snare hit detection for flash effects.
- 3 visual modes with auto-switch every 30 seconds.
- SPACE = manual mode switch, ESC = quit.
- Motion trails, particle bursts, ring fractals, spectrum tunnel, glitch overlays, hue-cycling neon palette, and subtle zoom drift.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install pygame sounddevice numpy
```

## Run

```bash
python main.py
```

Optional flags:

```bash
python main.py --width 1920 --height 1080 --fps 60 --samplerate 44100 --blocksize 1024 --device 1
```

> Tip: For system audio loopback, choose an appropriate input device (e.g. monitor/loopback device on your OS/audio stack).
