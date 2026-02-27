# Xbox 360 Rage Visualizer (Python)

A real-time, psychedelic music visualizer inspired by the Xbox 360 CD visualizer, now using **audio file playback inside the app** (no mic required).

## Features

- Open audio files from inside the app (`O`) using a file picker.
- Playback through `sounddevice.OutputStream` while sending the same live playback blocks to FFT analysis.
- Real-time NumPy FFT with bass/mid/high split and beat detection.
- 3 auto-switching visual modes (every 30s), plus manual mode switch (`M`).
- HUD debug overlay showing:
  - track name
  - current position / duration
  - play state
  - volume + bass/mid/high + beat flag
- Bottom equalizer bar graph (spectrum proof).
- Visual intensity gating: calmer visuals at very low volume, ramps up with louder audio.

## Supported audio formats

- Guaranteed: **WAV**, **FLAC** (via `soundfile/libsndfile`)
- Other formats (like MP3) depend on your local libsndfile build. If MP3 doesn’t load, convert to WAV/FLAC.

## Install

## Windows (PowerShell)

```powershell
cd C:\path\to\xbox360visulizer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## macOS/Linux

```bash
cd /path/to/xbox360visulizer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controls

- `O` = open audio file
- `SPACE` = play / pause
- `R` = restart from beginning
- `Left Arrow` = seek -5 seconds
- `Right Arrow` = seek +5 seconds
- `M` = switch visual mode manually
- `ESC` = quit

## Notes

- If no file is loaded, the app displays: **Press O to load audio**.
- For smooth performance, run at default settings first (`1280x720 @ 60 FPS`).
