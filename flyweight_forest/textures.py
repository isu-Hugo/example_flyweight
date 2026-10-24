"""Geração procedural das texturas das árvores (sem assets externos)."""

from __future__ import annotations

import random

import pygame

# Especificações dos tipos de árvore usados pela floresta.
# Cada tipo = estado intrínseco (nome, cor, "textura"/seed do sprite).
TREE_SPECS = [
    ("Carvalho", (34, 120, 45), 11),
    ("Pinheiro", (20, 90, 50), 22),
    ("Cerejeira", (220, 120, 160), 33),
    ("Bétula", (140, 190, 70), 44),
    ("Outono", (200, 110, 35), 55),
]


def make_tree_surface(color: tuple[int, int, int], seed: int,
                      width: int = 18, height: int = 24) -> pygame.Surface:
    """Desenha um sprite de árvore procedural.

    A aparência é determinada apenas por (color, seed): duas chamadas com os
    mesmos argumentos geram sprites idênticos — é isso que permite que o
    Flyweight compartilhe uma única Surface entre muitas árvores.
    """
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    rnd = random.Random(seed)

    # Tronco
    pygame.draw.rect(surf, (92, 64, 40), (width // 2 - 2, height - 8, 4, 8))

    # Copa: círculos sobrepostos com variação de tom
    cx, cy = width // 2, height // 2 - 2
    for _ in range(3):
        r = rnd.randint(5, 7)
        dx, dy = rnd.randint(-3, 3), rnd.randint(-3, 2)
        c = tuple(max(0, min(255, ch + rnd.randint(-18, 18))) for ch in color)
        pygame.draw.circle(surf, c, (cx + dx, cy + dy), r)

    return surf
