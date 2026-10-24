"""Aplicação pygame: floresta com toggle Flyweight <-> Naive + HUD de memória."""

from __future__ import annotations

import gc
import random
import time
import tracemalloc

import pygame

from .flyweight import Forest
from .naive import NaiveForest
from .textures import TREE_SPECS

WORLD_W, WORLD_H = 6000, 4000
TEX_W, TEX_H = 18, 24  # dimensões do sprite gerado em textures.py
BG = (18, 24, 18)
HUD_BG = pygame.Color(0, 0, 0, 170)


def _mb(n_bytes: int) -> float:
    return n_bytes / (1024 * 1024)


def _proc_status_kb(key: str) -> int:
    """Lê um valor em kB do /proc/self/status (ex.: VmRSS, VmHWM)."""
    with open("/proc/self/status") as fh:
        for line in fh:
            if line.startswith(key + ":"):
                return int(line.split()[1])
    return 0


def rss_mb() -> float:
    """Memória residente ATUAL do processo (a coluna MEM que o btop mostra)."""
    return _proc_status_kb("VmRSS") / 1024  # kB -> MB


def rss_peak_mb() -> float:
    """Pico de RSS do processo (equivalente ao high-water mark do btop)."""
    return _proc_status_kb("VmHWM") / 1024


class ForestApp:
    def __init__(self, tree_count: int, seed: int, mode: str = "flyweight",
                 show_hud: bool = True) -> None:
        self.tree_count = tree_count
        self.seed = seed
        self.mode = mode
        self.show_hud = show_hud
        self.forest = None
        self.cam_x = 0
        self.cam_y = 0
        self.status_msg = ""
        self.status_until = 0.0
        self.last_info: dict | None = None
        self.avg_fps = 0.0

    # ------------------------------------------------------------------
    def _build_forest(self, mode: str):
        """(Re)constrói a floresta do modo pedido, medindo o custo."""
        gc.collect()
        tracemalloc.reset_peak()
        before = tracemalloc.get_traced_memory()[0]

        rng = random.Random(self.seed)
        t0 = time.perf_counter()
        if mode == "flyweight":
            forest = Forest(WORLD_W, WORLD_H, TREE_SPECS)
        else:
            forest = NaiveForest(WORLD_W, WORLD_H, TREE_SPECS)
        forest.plant(self.tree_count, rng)
        elapsed = time.perf_counter() - t0

        current, peak = tracemalloc.get_traced_memory()
        if mode == "flyweight":
            surfaces = forest.factory.pool_size
        else:
            surfaces = forest.surfaces_created
        info = {
            "mode": mode,
            "trees": len(forest.trees),
            "alloc_mb": _mb(current - before),
            "peak_mb": _mb(peak),
            "rss_now_mb": rss_mb(),
            "rss_peak_mb": rss_peak_mb(),
            "surfaces": surfaces,
            "tex_mb": surfaces * TEX_W * TEX_H * 4 / (1024 * 1024),
            "elapsed_s": elapsed,
        }
        return forest, info

    def plant_initial(self) -> None:
        self.forest, info = self._build_forest(self.mode)
        self.last_info = info
        self._report(info)

    def toggle(self) -> None:
        self.mode = "naive" if self.mode == "flyweight" else "flyweight"
        self.forest, info = self._build_forest(self.mode)
        self.last_info = info
        self._report(info)
        self.status_msg = (f"Modo {self.mode.upper()} — plantio em "
                           f"{info['elapsed_s']:.2f}s | "
                           f"texturas {info['tex_mb']:.1f} MB "
                           f"({info['surfaces']} surfaces)")
        self.status_until = time.perf_counter() + 4.0

    @staticmethod
    def _report(info: dict) -> None:
        print(f"[{info['mode'].upper():9}] árvores={info['trees']:>7} | "
              f"Python heap={info['alloc_mb']:7.1f} MB | "
              f"texturas={info['surfaces']:>6} -> {info['tex_mb']:7.1f} MB | "
              f"RSS atual={info['rss_now_mb']:7.1f} MB | "
              f"RSS pico={info['rss_peak_mb']:7.1f} MB | "
              f"plantio={info['elapsed_s']:.2f}s")

    # ------------------------------------------------------------------
    def _draw_hud(self, screen: pygame.Surface, font: pygame.font.Font,
                  fps: float) -> None:
        f = self.forest
        if isinstance(f, Forest):
            tex = f.factory.pool_size * TEX_W * TEX_H * 4 / (1024 * 1024)
            lines = [
                f"Modo: FLYWEIGHT (padrao Flyweight)",
                f"Arvores (contextos): {len(f.trees):,}",
                f"TreeTypes (flyweights): {f.factory.types_created}",
                f"Objetos de dominio: {f.objects_created:,}",
                f"Texturas compartilhadas: {f.factory.pool_size} -> {tex:.1f} MB",
            ]
        else:
            tex = f.surfaces_created * TEX_W * TEX_H * 4 / (1024 * 1024)
            lines = [
                f"Modo: NAIVE (sem Flyweight)",
                f"Arvores: {len(f.trees):,}",
                f"Surfaces (uma por arvore): {f.surfaces_created:,} -> {tex:.1f} MB",
                f"Objetos de dominio: {f.objects_created:,}",
            ]

        current, peak = tracemalloc.get_traced_memory()
        lines += [
            "",
            f"Memoria Python (tracemalloc): {_mb(current):.1f} MB",
            f"Pico desde a troca de modo:   {_mb(peak):.1f} MB",
            f"RSS atual (coluna do btop):   {rss_mb():.1f} MB",
            f"RSS pico do processo:         {rss_peak_mb():.1f} MB",
            f"FPS: {fps:.0f}",
            "",
            "[F] trocar modo  |  [setas/mouse] mover  |  [ESC] sair",
        ]

        pad = 10
        line_h = font.get_linesize()
        box = pygame.Rect(0, 0, 560, pad * 2 + line_h * len(lines))
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill(HUD_BG)
        screen.blit(overlay, box.topleft)
        for i, text in enumerate(lines):
            color = (255, 220, 120) if text.startswith("[") else (230, 230, 230)
            screen.blit(font.render(text, True, color),
                        (pad, pad + i * line_h))

    def _draw_status(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        if time.perf_counter() > self.status_until:
            return
        surf = font.render(self.status_msg, True, (255, 255, 160))
        rect = surf.get_rect(midbottom=(screen.get_width() // 2,
                                        screen.get_height() - 12))
        bg = pygame.Rect(rect); bg.inflate_ip(16, 8)
        overlay = pygame.Surface(bg.size, pygame.SRCALPHA)
        overlay.fill(HUD_BG)
        screen.blit(overlay, bg.topleft)
        screen.blit(surf, rect)

    # ------------------------------------------------------------------
    def run(self, screen: pygame.Surface, duration: float | None = None) -> None:
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("monospace", 15)
        if font is None:
            font = pygame.font.Font(None, 20)
        view = screen.get_rect()
        self.cam_x = (WORLD_W - view.w) // 2
        self.cam_y = (WORLD_H - view.h) // 2
        speed = 18
        dragging = False
        drag_from = None
        started = time.perf_counter()
        frames = 0
        try:
            while True:
                if duration is not None and time.perf_counter() - started > duration:
                    return

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            return
                        if event.key == pygame.K_f:
                            self.toggle()
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        dragging = True
                        drag_from = event.pos
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        dragging = False
                    if event.type == pygame.MOUSEWHEEL:
                        self.cam_x -= event.x * 80
                        self.cam_y -= event.y * 80

                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    self.cam_x -= speed * 8
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    self.cam_x += speed * 8
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    self.cam_y -= speed * 8
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    self.cam_y += speed * 8
                if dragging:
                    dx = drag_from[0] - pygame.mouse.get_pos()[0]
                    dy = drag_from[1] - pygame.mouse.get_pos()[1]
                    self.cam_x += dx
                    self.cam_y += dy
                    drag_from = pygame.mouse.get_pos()

                self.cam_x = max(0, min(WORLD_W - view.w, self.cam_x))
                self.cam_y = max(0, min(WORLD_H - view.h, self.cam_y))

                screen.fill(BG)
                left, right = self.cam_x, self.cam_x + view.w
                top, bottom = self.cam_y, self.cam_y + view.h
                for tree in self.forest.trees:
                    if left <= tree.x <= right and top <= tree.y <= bottom:
                        tree.draw(screen, self.cam_x, self.cam_y)

                if self.show_hud:
                    self._draw_hud(screen, font, clock.get_fps())
                    self._draw_status(screen, font)

                pygame.display.flip()
                clock.tick(60)
                frames += 1
        finally:
            elapsed = time.perf_counter() - started
            self.avg_fps = frames / elapsed if elapsed > 0 else 0.0
            if self.last_info is not None:
                self.last_info["avg_fps"] = round(self.avg_fps, 1)
                self.last_info["rss_now_mb"] = rss_mb()
                self.last_info["rss_peak_mb"] = rss_peak_mb()
            pygame.quit()
