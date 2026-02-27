"""Xbox 360 inspired, modernized real-time music visualizer (file playback mode)."""

from __future__ import annotations

import argparse
import time
import tkinter as tk
from tkinter import filedialog

import pygame

from analyzer import AudioAnalyzer
from player import AudioFilePlayer
from visuals import VisualizerRenderer


def parse_args():
    parser = argparse.ArgumentParser(description="Real-time psychedelic music visualizer")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--blocksize", type=int, default=1024)
    return parser.parse_args()


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def pick_audio_file() -> str:
    root = tk.Tk()
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(
        title="Select audio file",
        filetypes=[
            ("Audio files", "*.wav *.flac *.aiff *.aif"),
            ("WAV", "*.wav"),
            ("FLAC", "*.flac"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return path


def main():
    args = parse_args()

    pygame.init()
    pygame.display.set_caption("Xbox 360 Rage Visualizer")
    screen = pygame.display.set_mode((args.width, args.height), pygame.SCALED | pygame.DOUBLEBUF)
    clock = pygame.time.Clock()

    player = AudioFilePlayer(blocksize=args.blocksize)
    analyzer = AudioAnalyzer(44100, args.blocksize)
    renderer = VisualizerRenderer(args.width, args.height)

    running = True
    last_mode_switch = time.monotonic()

    try:
        while running:
            dt = clock.tick(args.fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_o:
                        path = pick_audio_file()
                        if path:
                            player.load(path)
                            analyzer = AudioAnalyzer(player.samplerate, args.blocksize)
                            player.play()
                    elif event.key == pygame.K_SPACE:
                        player.toggle()
                    elif event.key == pygame.K_r:
                        player.restart()
                        player.play()
                    elif event.key == pygame.K_LEFT:
                        player.seek(-5.0)
                    elif event.key == pygame.K_RIGHT:
                        player.seek(5.0)
                    elif event.key == pygame.K_m:
                        renderer.next_mode()
                        last_mode_switch = time.monotonic()

            now = time.monotonic()
            if now - last_mode_switch >= 30:
                renderer.next_mode()
                last_mode_switch = now

            frame = player.get_last_block()
            state = analyzer.analyze(frame)

            info = player.get_info()
            hud = {
                "track": info.filename,
                "status": "Playing" if info.playing else ("Paused" if info.loaded else "No file loaded"),
                "time": f"{fmt_time(info.position_seconds)} / {fmt_time(info.duration_seconds)}",
            }

            renderer.update(dt, state)
            renderer.render(screen, state, hud=hud)

            if not info.loaded:
                text = "Press O to load audio"
                prompt = renderer.font.render(text, True, (255, 255, 255))
                screen.blit(prompt, (args.width // 2 - prompt.get_width() // 2, args.height // 2 - 20))

            pygame.display.flip()

    finally:
        player.close()
        pygame.quit()


if __name__ == "__main__":
    main()
