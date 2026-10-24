#!/usr/bin/env python
"""Demonstração do padrão Flyweight — Floresta.

Modo interativo (padrão):
    python main.py                      # 10.000 árvores, toggle com [F]

Comparação para o btop (dois terminais):
    python main.py --mode naive      --trees 50000
    python main.py --mode flyweight  --trees 50000

Extrações (fecha sozinho e imprime métricas):
    python main.py --mode naive --trees 50000 --duration 15
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tracemalloc

import pygame

from flyweight_forest.app import ForestApp, _mb, rss_mb, rss_peak_mb


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Flyweight: floresta demo em pygame")
    p.add_argument("--trees", type=int, default=10_000,
                   help="quantidade de árvores (padrão: 10000)")
    p.add_argument("--mode", choices=("flyweight", "naive"),
                   default="flyweight", help="modo inicial")
    p.add_argument("--duration", type=float, default=None,
                   help="fecha a janela após N segundos (para extrações)")
    p.add_argument("--no-hud", action="store_true", help="esconde o HUD")
    p.add_argument("--json", action="store_true",
                   help="imprime a linha final de métricas como JSON")
    p.add_argument("--seed", type=int, default=42, help="semente do plantio")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.trees <= 0:
        print("--trees deve ser > 0", file=sys.stderr)
        return 2

    # Permite rodar sem display (testes/CI) com SDL_VIDEODRIVER=dummy
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    tracemalloc.start()

    pygame.init()
    screen = pygame.display.set_mode((1280, 760))
    pygame.display.set_caption(
        f"Flyweight — Floresta ({args.mode}, {args.trees:,} árvores)")

    app = ForestApp(args.trees, args.seed, mode=args.mode,
                    show_hud=not args.no_hud)
    print(f"Plantando {args.trees:,} árvores no modo {args.mode}...")
    app.plant_initial()

    try:
        app.run(screen, duration=args.duration)
    finally:
        current, peak = tracemalloc.get_traced_memory()
        info = dict(app.last_info or {})
        info.update(mode=app.mode, trees=args.trees,
                    tracemalloc_mb=round(_mb(current), 2),
                    tracemalloc_peak_mb=round(_mb(peak), 2))
        if args.json:
            print("METRICS " + json.dumps(info))
        else:
            print("--- resumo final ---")
            print(f"modo={app.mode} árvores={args.trees:,} "
                  f"FPS médio={info.get('avg_fps', 0):.0f}")
            print(f"tracemalloc atual={_mb(current):.1f} MB "
                  f"pico={_mb(peak):.1f} MB | RSS atual={rss_mb():.1f} MB | "
                  f"RSS pico={rss_peak_mb():.1f} MB")
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
