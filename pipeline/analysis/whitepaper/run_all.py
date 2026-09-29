"""Einziger Einstiegspunkt fuer die White-Paper-Analyse.

Ruft, in dieser Reihenfolge, ``zaehlen`` (ein Durchlauf ueber das TIF,
Selbstpruefungen, Cache in einem Temp-Verzeichnis), dann ``tabellen``
(Markdown/CSV nach ``docs/whitepaper/tabellen/``) und dann ``abbildungen``
(PNG+SVG nach ``docs/whitepaper/abb/``) auf.

Alle Zahlen stammen ausschliesslich aus dem TIF plus Manifest. Die
Bundeslandgrenzen-Rohquelle (``--grenzen``) wird ausschliesslich verwendet,
um Zellen Bundeslaendern zuzuordnen (Bezugsflaeche) und um Kartenumrisse zu
zeichnen.

Beispiel:
    uv run python -m pipeline.analysis.whitepaper.run_all \\
        --tif out/abschichtung.tif --manifest out/abschichtung.bands.json \\
        --grenzen data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import abbildungen, tabellen, zaehlen

REPO_ROOT = Path(__file__).resolve().parents[3]  # .../abschichtung (pipeline/analysis/whitepaper/run_all.py)
DEFAULT_OUT_ROOT = REPO_ROOT / "docs" / "whitepaper"

DEFAULT_TIF = REPO_ROOT / "out" / "abschichtung.tif"
DEFAULT_MANIFEST = REPO_ROOT / "out" / "abschichtung.bands.json"
DEFAULT_GRENZEN = REPO_ROOT / "data" / "admin" / "VGD_Oesterreich_gen_50_20221002" / "VGD_50_generalisiert.shp"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tif", type=Path, default=DEFAULT_TIF)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--grenzen", type=Path, default=DEFAULT_GRENZEN)
    ap.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    ap.add_argument("--sha256", default=None, help="erwarteter sha256 des TIF (optional)")
    args = ap.parse_args()

    print("=" * 70)
    print("[run_all] 1/3 zaehlen.py")
    print("=" * 70)
    cache_dir = zaehlen.run(args.tif, args.manifest, args.grenzen, args.sha256)

    print("=" * 70)
    print("[run_all] 2/3 tabellen.py")
    print("=" * 70)
    tabellen_dir = tabellen.run(cache_dir, args.manifest, args.grenzen, args.out_root)

    print("=" * 70)
    print("[run_all] 3/3 abbildungen.py")
    print("=" * 70)
    abb_dir = abbildungen.run(cache_dir, args.grenzen, args.out_root)

    print("=" * 70)
    print("[run_all] fertig")
    print(f"  Cache (Temp, nicht im Repo): {cache_dir}")
    print(f"  Tabellen: {tabellen_dir}")
    print(f"  Abbildungen: {abb_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
