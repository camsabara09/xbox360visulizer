"""Pygame visual rendering module for chaotic music-reactive visuals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

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

        self.trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)

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
            speed = random.uniform(2.0, 8.0) + bass * 0.01
            self.particles.append(
                Particle(
                    x=self.center.x,
                    y=self.center.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.uniform(0.4, 1.0),
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
        self.hue = (self.hue + 60 * dt + state.high * 0.002) % 360
        self.bg_phase += dt * (0.4 + state.mid * 0.0002)
        self.zoom = 1.0 + 0.02 * math.sin(self.bg_phase * 0.7) + min(0.1, state.volume * 1.3)

        if state.beat:
            self.shake = min(25.0, self.shake + 8 + state.bass * 0.03)
            self.flash = min(200.0, self.flash + 55)
            self.spawn_burst(45, state.bass)
            self.spawn_ring(state.bass)

        if state.treble_hit:
            self.flash = min(255.0, self.flash + 80)
            self.spawn_burst(18, state.high)

        self.shake *= 0.88
        self.flash *= 0.82

        drag = max(0.7, 1.0 - dt * 2.0)
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= drag
            p.vy *= drag
            p.life -= dt * 0.9
            p.size *= 0.995
        self.particles = [p for p in self.particles if p.life > 0 and p.size > 0.5]

        for r in self.rings:
            r.radius += r.speed + state.bass * 0.003
            r.life -= dt * 0.55
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

    def _draw_spectrum_tunnel(self, screen: pygame.Surface, state: AnalysisState, offset: pygame.Vector2):
        bins = min(128, len(state.spectrum))
        spec = state.spectrum[:bins]
        base_radius = min(self.width, self.height) * 0.18
        for i, amp in enumerate(spec[::2]):
            angle = (i / (bins / 2)) * math.tau + self.bg_phase * 0.4
            depth = 1 + i * 0.09
            radius = base_radius * depth * self.zoom
            pulse = amp * 220 + state.bass * 0.005
            x = self.center.x + math.cos(angle) * (radius + pulse) + offset.x
            y = self.center.y + math.sin(angle) * (radius + pulse) + offset.y
            color = self.hsv_to_rgb(self.hue + i * 4, 90, 35 + amp * 70)
            pygame.draw.circle(self.glow_surface, (*color, 65), (int(x), int(y)), int(2 + amp * 5))

    def _draw_geometry(self, screen: pygame.Surface, state: AnalysisState, offset: pygame.Vector2):
        bass_scale = 1.0 + min(1.4, state.bass * 0.006)
        size = min(self.width, self.height) * 0.11 * bass_scale * self.zoom
        points = []
        count = 6 if self.mode_index == 0 else 8 if self.mode_index == 1 else 5
        for i in range(count):
            angle = (i / count) * math.tau + self.bg_phase * (0.7 + self.mode_index * 0.25)
            radius = size * (1 + 0.3 * math.sin(self.bg_phase * 2 + i))
            points.append(
                (
                    self.center.x + math.cos(angle) * radius + offset.x,
                    self.center.y + math.sin(angle) * radius + offset.y,
                )
            )
        color = self.hsv_to_rgb(self.hue + 50, 95, 80)
        pygame.draw.polygon(screen, color, points, width=3)

    def _draw_rings(self, screen: pygame.Surface, offset: pygame.Vector2):
        for r in self.rings:
            color = self.hsv_to_rgb(r.hue, 90, 80 * r.life)
            pygame.draw.circle(
                self.glow_surface,
                (*color, int(100 * r.life)),
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
                (*color, int(220 * p.life)),
                (int(p.x + offset.x), int(p.y + offset.y)),
                int(p.size),
            )

    def render(self, screen: pygame.Surface, state: AnalysisState):
        shake_vec = pygame.Vector2(
            random.uniform(-self.shake, self.shake),
            random.uniform(-self.shake, self.shake),
        )

        self.trail_surface.fill((0, 0, 0, 35))
        screen.blit(self.trail_surface, (0, 0))
        self._draw_background(screen, state, shake_vec)

        self.glow_surface.fill((0, 0, 0, 0))

        if self.mode_index == 0:
            self._draw_spectrum_tunnel(screen, state, shake_vec)
            self._draw_geometry(screen, state, shake_vec)
        elif self.mode_index == 1:
            self._draw_geometry(screen, state, shake_vec)
            self._draw_spectrum_tunnel(screen, state, shake_vec)
        else:
            self._draw_spectrum_tunnel(screen, state, shake_vec)
            self._draw_geometry(screen, state, shake_vec)
            if state.beat:
                for _ in range(8):
                    x = random.randint(0, self.width)
                    w = random.randint(10, 50)
                    col = self.hsv_to_rgb(self.hue + random.randint(0, 120), 90, 90)
                    pygame.draw.rect(self.glow_surface, (*col, 60), (x, 0, w, self.height))

        self._draw_rings(screen, shake_vec)
        self._draw_particles(shake_vec)

        if self.flash > 1:
            flash_col = self.hsv_to_rgb(self.hue + 180, 40, min(100, self.flash * 0.5))
            pygame.draw.rect(
                self.glow_surface,
                (*flash_col, int(min(180, self.flash))),
                (0, 0, self.width, self.height),
            )

        screen.blit(self.glow_surface, (0, 0), special_flags=pygame.BLEND_ADD)
