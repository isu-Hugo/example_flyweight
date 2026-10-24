"""Contra-exemplo SEM o padrão Flyweight.

Cada NaiveTree guarda cópia própria do estado que deveria ser compartilhado:
a cor, o nome E a Surface inteira da textura. É esse desperdício que a
demonstração quer evidenciar.
"""

from __future__ import annotations

import random

import pygame

from .textures import make_tree_surface


class NaiveTree:
    """Sem Flyweight: tudo duplicado por instância."""

    __slots__ = ("x", "y", "name", "color", "surface")

    def __init__(self, x: int, y: int, name: str,
                 color: tuple[int, int, int], seed: int) -> None:
        self.x = x
        self.y = y
        self.name = name  # duplicado N vezes
        self.color = color  # duplicado N vezes
        # Cada árvore tem sua PRÓPRIA Surface (mesmo conteúdo das outras)
        self.surface = make_tree_surface(color, seed).convert_alpha()

    def draw(self, screen: pygame.Surface, cam_x: int, cam_y: int) -> None:
        screen.blit(self.surface, self.surface.get_rect(center=(
            self.x - cam_x, self.y - cam_y)))


class NaiveForest:
    def __init__(self, world_w: int, world_h: int, specs) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.specs = specs
        self.trees: list[NaiveTree] = []
        self.surfaces_created = 0  # métrica: quantas Surface existem

    def plant(self, count: int, rng: random.Random) -> None:
        for _ in range(count):
            name, color, seed = rng.choice(self.specs)
            x = rng.randint(0, self.world_w)
            y = rng.randint(0, self.world_h)
            self.trees.append(NaiveTree(x, y, name, color, seed))
            self.surfaces_created += 1
        self.trees.sort(key=lambda t: t.y)

    @property
    def objects_created(self) -> int:
        return len(self.trees)
