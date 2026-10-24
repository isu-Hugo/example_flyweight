#!/usr/bin/env python
"""Gera a tabela Flyweight vs Naive rodando cada caso em processo separado.

Cada combinação (N árvores x modo) vira um processo novo — por isso o RSS
mostrado é honesto e comparável (é o mesmo número que aparece no btop).

Uso:
    python compare.py                       # N = 10k, 50k, 100k
    python compare.py --trees 5000 20000 200000
    python compare.py --out resultados.md
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_case(mode: str, trees: int, duration: float) -> dict:
    env = {**os.environ, "SDL_VIDEODRIVER": os.environ.get("SDL_VIDEODRIVER", "")}
    if not env["SDL_VIDEODRIVER"]:
        env.pop("SDL_VIDEODRIVER")
    cmd = [sys.executable, str(ROOT / "main.py"), "--mode", mode,
           "--trees", str(trees), "--duration", str(duration), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
    for line in proc.stdout.splitlines():
        if line.startswith("METRICS "):
            return json.loads(line[8:])
    print(proc.stdout, file=sys.stderr)
    print(proc.stderr, file=sys.stderr)
    raise SystemExit(f"falha ao executar: {' '.join(cmd)}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trees", type=int, nargs="+",
                   default=[10_000, 50_000, 100_000])
    p.add_argument("--duration", type=float, default=3.0,
                   help="segundos que cada janela fica aberta")
    p.add_argument("--out", type=Path, default=None,
                   help="salva a tabela markdown em um arquivo")
    args = p.parse_args()

    rows = []
    for n in args.trees:
        print(f"-> {n:,} árvores...", file=sys.stderr)
        for mode in ("flyweight", "naive"):
            m = run_case(mode, n, args.duration)
            rows.append(m)

    header = ("| Árvores | Modo | Texturas | Mem. texturas | Heap Python | "
              "RSS (btop) | Plantio | FPS |\n"
              "|---:|---|---:|---:|---:|---:|---:|---:|")
    lines = [header]
    for m in rows:
        lines.append(
            f"| {m['trees']:,} | {m['mode']} | {m['surfaces']:,} | "
            f"{m['tex_mb']:.1f} MB | {m['alloc_mb']:.1f} MB | "
            f"{m['rss_now_mb']:.1f} MB | {m['elapsed_s']:.2f}s | "
            f"{m.get('avg_fps', 0):.0f} |")
    table = "\n".join(lines)
    print(table)

    # Resumo: quanto custa NÃO usar o Flyweight
    print("\n### Diferença (naive - flyweight)\n")
    print("| Árvores | Δ RSS | Δ mem. texturas | Δ plantio |\n|---:|---:|---:|---:|")
    by_n: dict[int, dict[str, dict]] = {}
    for m in rows:
        by_n.setdefault(m["trees"], {})[m["mode"]] = m
    for n, pair in sorted(by_n.items()):
        fw, nv = pair["flyweight"], pair["naive"]
        print(f"| {n:,} | +{nv['rss_now_mb'] - fw['rss_now_mb']:.1f} MB | "
              f"+{nv['tex_mb'] - fw['tex_mb']:.1f} MB | "
              f"+{nv['elapsed_s'] - fw['elapsed_s']:.2f}s |")

    if args.out:
        args.out.write_text(table + "\n", encoding="utf-8")
        print(f"tabela salva em {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
