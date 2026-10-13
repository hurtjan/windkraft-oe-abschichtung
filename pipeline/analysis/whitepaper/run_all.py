"""Einziger Einstiegspunkt fuer die White-Paper-Analyse.

Ruft, in dieser Reihenfolge, ``zaehlen`` (ein Durchlauf ueber das TIF,
Selbstpruefungen, Cache in einem Temp-Verzeichnis), ``tabellen``
(Markdown/CSV nach ``docs/whitepaper/tabellen/``), ``landnutzung``,
``streusiedlung_umfang`` und ``weitere_zahlen`` (Zahlen + Register),
``abbildungen`` (PNG+SVG nach ``docs/whitepaper/abb/``) und zuletzt ``render``
auf: ``docs/whitepaper/paper_vorlage.md`` -> ``docs/whitepaper/paper.md``
(Platzhalter aus ``tabellen/zahlen.json``). Die Vorlage ist die Quelle des Papers.

Alle Zahlen stammen ausschliesslich aus dem TIF plus Manifest. Die
Bundeslandgrenzen-Rohquelle (``--grenzen``) wird ausschliesslich verwendet,
um Zellen Bundeslaendern zuzuordnen (Bezugsflaeche) und um Kartenumrisse zu
zeichnen.

Beispiel:
    uv run python -m pipeline.analysis.whitepaper.run_all \\
        --tif out/abschichtung.tif --manifest out/abschichtung.bands.json \\
        --grenzen derived/prep/admin/bundesland_masken.parquet
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import contract
from . import (abbildungen, beispielkarten, landnutzung, natur_ebenen, render, streusiedlung_umfang, tabellen, weitere_zahlen,
               zahlen, zahlen_tabellen, zaehlen)

REPO_ROOT = Path(__file__).resolve().parents[3]  # .../abschichtung (pipeline/analysis/whitepaper/run_all.py)
DEFAULT_OUT_ROOT = REPO_ROOT / "docs" / "whitepaper"

DEFAULT_TIF = REPO_ROOT / "out" / "abschichtung.tif"
DEFAULT_MANIFEST = REPO_ROOT / "out" / "abschichtung.bands.json"
DEFAULT_ANALYSE_TIF = REPO_ROOT / "out" / "abschichtung_analyse.tif"
DEFAULT_ANALYSE_MANIFEST = REPO_ROOT / "out" / "abschichtung_analyse.bands.json"
DEFAULT_GRENZEN = contract.PREP_FILES["admin"]["bundesland_masken"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tif", type=Path, default=DEFAULT_TIF)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--analyse-tif", type=Path, default=DEFAULT_ANALYSE_TIF)
    ap.add_argument("--analyse-manifest", type=Path, default=DEFAULT_ANALYSE_MANIFEST)
    ap.add_argument("--grenzen", type=Path, default=DEFAULT_GRENZEN)
    ap.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    ap.add_argument("--sha256", default=None, help="erwarteter sha256 des TIF (optional)")
    args = ap.parse_args()

    vorlage = args.out_root / "paper_vorlage.md"
    if not vorlage.is_file():
        raise SystemExit(f"Vorlage fehlt: {vorlage} (Quelle des White Papers; ohne sie kann nicht gerendert werden).")
    zahlen.reset()

    for need in (args.analyse_tif, args.analyse_manifest):
        if not Path(need).exists():
            raise SystemExit(f"Analyse-Raster fehlt: {need} (zuerst `make analyse-raster`).")

    print("=" * 70)
    print("[run_all] 1/7 zaehlen.py")
    print("=" * 70)
    cache_dir = zaehlen.run(args.tif, args.manifest, args.grenzen, args.sha256)

    print("=" * 70)
    print("[run_all] 2/7 tabellen.py")
    print("=" * 70)
    tabellen_dir = tabellen.run(cache_dir, args.manifest, args.grenzen, args.out_root)

    print("=" * 70)
    print("[run_all] 3/7 landnutzung.py (L1, Analyse-Raster)")
    print("=" * 70)
    prov = json.loads((cache_dir / "provenance.json").read_text(encoding="utf-8"))
    landnutzung.run(args.tif, args.manifest, args.grenzen, args.out_root,
                    args.analyse_tif, args.analyse_manifest, main_sha256=prov["tif_sha256"])

    print("=" * 70)
    print("[run_all] 4/7 Zahlenregister (K, T1, D1-D3, L1)")
    print("=" * 70)
    zahlen_tabellen.run(tabellen_dir)

    print("=" * 70)
    print("[run_all] 5/7 streusiedlung_umfang.py + weitere_zahlen.py")
    print("=" * 70)
    streusiedlung_umfang.run(args.tif, args.manifest, args.grenzen, args.out_root,
                             prov["tif_sha256"], prov["tif_date"])
    weitere_zahlen.run(args.tif, args.manifest, args.grenzen)
    # N1: Zaehlung der UBA-Eingabedaten (Ausnahme von der TIF-only-Regel, siehe natur_ebenen.py)    natur_ebenen.run(args.out_root, contract.PREP_FILES["natur"]["schutzgebiete"])
    # Abb. 3 und Abb. 4 (Beispielkarten) vor dem Render; Zahlen von Abb. 3 ins Register
    beispielkarten.run(args.out_root, args.tif, args.manifest)
    # Textfelder (Gemeinde, GKZ) sind keine Registerzahlen -> ueberspringen
    beispielkarten.register_numbers(
        lambda k, w, e, q: zahlen.register(k, w, e, q) if isinstance(w, (int, float)) else None, args.out_root)
    sha12 = prov["tif_sha256"][:12]
    register = zahlen.write(tabellen_dir / "zahlen.json", sha12)
    print(f"[run_all] Zahlenregister: {len(register)} Schluessel -> {tabellen_dir / 'zahlen.json'}")

    print("=" * 70)
    print("[run_all] 6/7 abbildungen.py")
    print("=" * 70)
    abb_dir = abbildungen.run(cache_dir, args.grenzen, args.out_root)

    print("=" * 70)
    print("[run_all] 7/7 render.py (paper_vorlage.md -> paper.md)")
    print("=" * 70)
    render.run(vorlage, args.out_root / "paper.md", register, tabellen_dir, sha12, prov["tif_date"])

    print("=" * 70)
    print("[run_all] fertig")
    print(f"  Cache (Temp, nicht im Repo): {cache_dir}")
    print(f"  Tabellen: {tabellen_dir}")
    print(f"  Abbildungen: {abb_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
