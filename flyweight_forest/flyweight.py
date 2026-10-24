"""Implementação do padrão Flyweight.

TreeType  -> o FLYWEIGHT: guarda o estado intrínseco (nome, cor, textura).
Tree      -> o CONTEXTO:   guarda apenas o estado extrínseco (x, y) e uma
              referência ao flyweight compartilhado.
TreeFactory -> a FÁBRICA:  mantém o pool de flyweights e garante que cada
              combinação de estado intrínseco seja criada uma única vez.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from .textures import make_tree_surface


@dataclass(frozen=True)
class TreeType:
    """Flyweight: estado intrínseco, IMUTÁVEL e compartilhado."""

    name: str
    color: tuple[int, int, int]
    surface: pygame.Surface

    def draw(self, screen: pygame.Surface, x: int, y: int) -> None:
        screen.blit(self.surface, self.surface.get_rect(center=(x, y)))


class TreeFactory:
    """Fábrica de flyweights: o pool evita duplicar objetos iguais."""

    def __init__(self) -> None:
        self._pool: dict[tuple, TreeType] = {}
        self.types_created = 0  # métrica para o HUD/prova didática

    def get_type(self, name: str, color: tuple[int, int, int], seed: int) -> TreeType:
        key = (name, color, seed)
        tree_type = self._pool.get(key)
        if tree_type is None:
            surface = make_tree_surface(color, seed).convert_alpha()
            tree_type = TreeType(name, color, surface)
            self._pool[key] = tree_type
            self.types_created += 1
        return tree_type

    @property
    def pool_size(self) -> int:
        return len(self._pool)


class Tree:
    """Contexto: cada árvore tem posição própria, mas reutiliza o TreeType."""

    __slots__ = ("x", "y", "tree_type")

    def __init__(self, x: int, y: int, tree_type: TreeType) -> None:
        self.x = x
        self.y = y
        self.tree_type = tree_type

    def draw(self, screen: pygame.Surface, cam_x: int, cam_y: int) -> None:
        self.tree_type.draw(screen, self.x - cam_x, self.y - cam_y)


class Forest:
    def __init__(self, world_w: int, world_h: int, specs) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.specs = specs
        self.factory = TreeFactory()
        self.trees: list[Tree] = []

    def plant(self, count: int, rng: random.Random) -> None:
        for _ in range(count):
            name, color, seed = rng.choice(self.specs)
            tree_type = self.factory.get_type(name, color, seed)
            x = rng.randint(0, self.world_w)
            y = rng.randint(0, self.world_h)
            self.trees.append(Tree(x, y, tree_type))
        # Profundidade falsa: desenhar de trás para frente (menor y primeiro)
        self.trees.sort(key=lambda t: t.y)

    @property
    def objects_created(self) -> int:
        """Objetos de domínio vivos: 1 TreeType + N Trees."""
        return self.factory.types_created + len(self.trees)
