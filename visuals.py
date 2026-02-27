"""Pygame visual rendering module for chaotic music-reactive visuals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pygame

from analyzer import AnalysisState

Color = Tuple[int, int, int]


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    hue: float


@dataclass
class Ring:
    x: float
    y: float
    radius: float
    speed: float
    life: float
    hue: float


class VisualizerRenderer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.center = pygame.Vector2(width / 2, height / 2)

        self.particles: List[Particle] = []
        self.rings: List[Ring] = []

        self.hue = 0.0
        self.bg_phase = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.zoom = 1.0
        self.mode_index = 0
        self.intensity = 0.0

        self.trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 14)

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % 3

    @staticmethod
    def hsv_to_rgb(h: float, s: float, v: float) -> Color:
        color = pygame.Color(0)
        color.hsva = (h % 360, max(0, min(100, s)), max(0, min(100, v)), 100)
        return color.r, color.g, color.b

    def spawn_burst(self, amount: int, bass: float):
        for _ in range(amount):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.8, 7.5) + bass * 0.01
            self.particles.append(
                Particle(
                    x=self.center.x,
                    y=self.center.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.uniform(0.35, 1.0),
                    size=random.uniform(2.0, 6.0),
                    hue=(self.hue + random.uniform(-60, 60)) % 360,
                )
            )

    def spawn_ring(self, bass: float):
        self.rings.append(
            Ring(
                x=self.center.x,
                y=self.center.y,
                radius=20 + bass * 0.04,
                speed=3.0 + bass * 0.02,
                life=1.0,
                hue=self.hue,
            )
        )

    def update(self, dt: float, state: AnalysisState):
        target_intensity = min(1.0, max(0.0, (state.volume - 0.012) / 0.10))
        self.intensity = self.intensity * 0.92 + target_intensity * 0.08

        self.hue = (self.hue + (30 + 45 * self.intensity) * dt + state.high * 0.0015) % 360
        self.bg_phase += dt * (0.25 + self.intensity + state.mid * 0.0002)
        self.zoom = 1.0 + 0.02 * math.sin(self.bg_phase * 0.7) + min(0.08, state.volume)

        if state.beat and self.intensity > 0.08:
            self.shake = min(25.0, self.shake + (2 + 11 * self.intensity) + state.bass * 0.02)
            self.flash = min(200.0, self.flash + 15 + 55 * self.intensity)
            self.spawn_burst(int(12 + 48 * self.intensity), state.bass)
            self.spawn_ring(state.bass)

        if state.treble_hit and self.intensity > 0.12:
            self.flash = min(255.0, self.flash + 25 + 70 * self.intensity)
            self.spawn_burst(int(8 + 22 * self.intensity), state.high)

        self.shake *= 0.86
        self.flash *= 0.80

        drag = max(0.7, 1.0 - dt * 2.0)
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= drag
            p.vy *= drag
            p.life -= dt * (0.8 + 0.3 * self.intensity)
            p.size *= 0.995
        self.particles = [p for p in self.particles if p.life > 0 and p.size > 0.5]

        for r in self.rings:
            r.radius += r.speed + state.bass * 0.002
            r.life -= dt * (0.45 + 0.25 * self.intensity)
        self.rings = [r for r in self.rings if r.life > 0]

        if len(self.particles) > 1200:
            self.particles = self.particles[-1200:]
        if len(self.rings) > 120:
            self.rings = self.rings[-120:]

    def _draw_background(self, screen: pygame.Surface, state: AnalysisState, offset: pygame.Vector2):
        mid_inf = min(1.0, state.mid * 0.003)
        high_inf = min(1.0, state.high * 0.004)
        c1 = self.hsv_to_rgb(self.hue + 30 * math.sin(self.bg_phase), 70 + 20 * high_inf, 9 + 20 * mid_inf)
        c2 = self.hsv_to_rgb(self.hue + 160 + 40 * math.cos(self.bg_phase * 1.2), 75, 8 + 24 * high_inf)

        for y in range(0, self.height, 4):
            t = y / max(1, self.height - 1)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            pygame.draw.rect(screen, (r, g, b), (offset.x, y + offset.y, self.width, 4))

    def _draw_spectrum_tunnel(self, state: AnalysisState, offset: pygame.Vector2):
        bins = min(128, len(state.spectrum))
        spec = state.spectrum[:bins]
        base_radius = min(self.width, self.height) * 0.18
        for i, amp in enumerate(spec[::2]):
            angle = (i / (bins / 2)) * math.tau + self.bg_phase * (0.2 + 0.3 * self.intensity)
            depth = 1 + i * 0.09
            radius = base_radius * depth * self.zoom
            pulse = amp * (120 + 160 * self.intensity) + state.bass * 0.004
            x = self.center.x + math.cos(angle) * (radius + pulse) + offset.x
            y = self.center.y + math.sin(angle) * (radius + pulse) + offset.y
            color = self.hsv_to_rgb(self.hue + i * 4, 90, 35 + amp * 70)
            pygame.draw.circle(self.glow_surface, (*color, int(20 + 55 * self.intensity)), (int(x), int(y)), int(2 + amp * 5))

    def _draw_geometry(self, screen: pygame.Surface, state: AnalysisState, offset: pygame.Vector2):
        bass_scale = 1.0 + min(1.2, state.bass * 0.005)
        size = min(self.width, self.height) * 0.11 * bass_scale * self.zoom
        points = []
        count = 6 if self.mode_index == 0 else 8 if self.mode_index == 1 else 5
        for i in range(count):
            angle = (i / count) * math.tau + self.bg_phase * (0.5 + self.mode_index * 0.2)
            radius = size * (1 + 0.3 * math.sin(self.bg_phase * 2 + i))
            points.append((self.center.x + math.cos(angle) * radius + offset.x, self.center.y + math.sin(angle) * radius + offset.y))
        color = self.hsv_to_rgb(self.hue + 50, 95, 55 + 45 * self.intensity)
        pygame.draw.polygon(screen, color, points, width=3)

    def _draw_rings(self, offset: pygame.Vector2):
        for r in self.rings:
            color = self.hsv_to_rgb(r.hue, 90, 80 * r.life)
            pygame.draw.circle(
                self.glow_surface,
                (*color, int(80 * r.life * max(0.2, self.intensity + 0.2))),
                (int(r.x + offset.x), int(r.y + offset.y)),
                int(r.radius),
                width=2,
            )

    def _draw_particles(self, offset: pygame.Vector2):
        for p in self.particles:
            v = min(100, 20 + p.life * 80)
            color = self.hsv_to_rgb(p.hue, 90, v)
            pygame.draw.circle(
                self.glow_surface,
                (*color, int(220 * p.life * max(0.2, self.intensity + 0.2))),
                (int(p.x + offset.x), int(p.y + offset.y)),
                int(p.size),
            )

    def _draw_hud(self, screen: pygame.Surface, state: AnalysisState, hud: Dict[str, str | float | bool]):
        hud_bg = pygame.Surface((self.width, 122), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 120))
        screen.blit(hud_bg, (0, 0))

        track = str(hud.get("track", ""))
        status = str(hud.get("status", ""))
        time_text = str(hud.get("time", "0:00 / 0:00"))
        line1 = f"Track: {track if track else 'None loaded'}"
        line2 = f"State: {status} | Time: {time_text} | Mode: {self.mode_index + 1}"
        line3 = f"Vol: {state.volume:.4f}  Bass: {state.bass:.2f}  Mid: {state.mid:.2f}  High: {state.high:.2f}  Beat: {state.beat}"

        screen.blit(self.font.render(line1, True, (230, 230, 230)), (12, 10))
        screen.blit(self.small_font.render(line2, True, (200, 200, 200)), (12, 38))
        screen.blit(self.small_font.render(line3, True, (200, 255, 220)), (12, 58))

        meter_w = 240
        meter_h = 14
        mx, my = 12, 84
        pygame.draw.rect(screen, (40, 40, 40), (mx, my, meter_w, meter_h))
        fill = int(min(1.0, state.volume * 18) * meter_w)
        pygame.draw.rect(screen, (70, 220, 140), (mx, my, fill, meter_h))
        pygame.draw.rect(screen, (130, 130, 130), (mx, my, meter_w, meter_h), 1)
        screen.blit(self.small_font.render("Volume", True, (220, 220, 220)), (mx + meter_w + 8, my - 1))

    def _draw_bottom_equalizer(self, screen: pygame.Surface, spectrum):
        bins = min(60, len(spectrum))
        if bins <= 0:
            return
        bar_w = self.width / bins
        base_y = self.height - 8
        max_h = int(self.height * 0.14)
        for i in range(bins):
            amp = float(spectrum[i])
            h = int(max_h * min(1.0, amp * 2.2))
            x = int(i * bar_w)
            color = self.hsv_to_rgb(self.hue + i * 4, 90, 50 + amp * 50)
            pygame.draw.rect(screen, color, (x, base_y - h, max(1, int(bar_w - 1)), h))

    def render(self, screen: pygame.Surface, state: AnalysisState, hud: Dict[str, str | float | bool] | None = None):
        shake_amount = self.shake * max(0.15, self.intensity)
        shake_vec = pygame.Vector2(random.uniform(-shake_amount, shake_amount), random.uniform(-shake_amount, shake_amount))

        trail_alpha = int(50 - 25 * self.intensity)
        self.trail_surface.fill((0, 0, 0, trail_alpha))
        screen.blit(self.trail_surface, (0, 0))
        self._draw_background(screen, state, shake_vec)

        self.glow_surface.fill((0, 0, 0, 0))

        if self.mode_index == 0:
            self._draw_spectrum_tunnel(state, shake_vec)
            self._draw_geometry(screen, state, shake_vec)
        elif self.mode_index == 1:
            self._draw_geometry(screen, state, shake_vec)
            self._draw_spectrum_tunnel(state, shake_vec)
        else:
            self._draw_spectrum_tunnel(state, shake_vec)
            self._draw_geometry(screen, state, shake_vec)
            if state.beat and self.intensity > 0.2:
                for _ in range(int(2 + 8 * self.intensity)):
                    x = random.randint(0, self.width)
                    w = random.randint(10, 50)
                    col = self.hsv_to_rgb(self.hue + random.randint(0, 120), 90, 90)
                    pygame.draw.rect(self.glow_surface, (*col, int(20 + 70 * self.intensity)), (x, 0, w, self.height))

        self._draw_rings(shake_vec)
        self._draw_particles(shake_vec)

        if self.flash > 1 and self.intensity > 0.05:
            flash_col = self.hsv_to_rgb(self.hue + 180, 40, min(100, self.flash * 0.5))
            pygame.draw.rect(self.glow_surface, (*flash_col, int(min(160, self.flash * self.intensity))), (0, 0, self.width, self.height))

        screen.blit(self.glow_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        self._draw_bottom_equalizer(screen, state.spectrum)

        if hud is not None:
            self._draw_hud(screen, state, hud)
