"""Xbox 360 inspired, modernized real-time music visualizer."""

from __future__ import annotations

import argparse
import time

import pygame

from analyzer import AudioAnalyzer
from audio_input import AudioConfig, AudioInput
from visuals import VisualizerRenderer


def parse_args():
    parser = argparse.ArgumentParser(description="Real-time psychedelic music visualizer")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--samplerate", type=int, default=44100)
    parser.add_argument("--blocksize", type=int, default=1024)
    parser.add_argument("--device", type=int, default=None, help="Input device id for sounddevice")
    return parser.parse_args()


def main():
    args = parse_args()

    pygame.init()
    pygame.display.set_caption("Xbox 360 Rage Visualizer")
    screen = pygame.display.set_mode((args.width, args.height), pygame.SCALED | pygame.DOUBLEBUF)
    clock = pygame.time.Clock()

    audio = AudioInput(
        AudioConfig(
            samplerate=args.samplerate,
            blocksize=args.blocksize,
            channels=1,
            device=args.device,
        )
    )
    analyzer = AudioAnalyzer(args.samplerate, args.blocksize)
    renderer = VisualizerRenderer(args.width, args.height)

    audio.start()
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
                    elif event.key == pygame.K_SPACE:
                        renderer.next_mode()
                        last_mode_switch = time.monotonic()

            now = time.monotonic()
            if now - last_mode_switch >= 30:
                renderer.next_mode()
                last_mode_switch = now

            frame = audio.get_latest_frame()
            state = analyzer.analyze(frame)
            renderer.update(dt, state)
            renderer.render(screen, state)

            pygame.display.flip()

    finally:
        audio.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
