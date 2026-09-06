"""Leitet die NÖ-HiG-Quellobjekte aus den bereits extrahierten SekROP-Zonen ab.

Reine Vektorverarbeitung (keine PDF-Abhängigkeit): liest
output/noe/pdf_750m_*.geojson und schreibt output/noe/pdf_hig_source_*.geojson.
Methode und Garantien siehe windkraft/noe/pdf_hig_sources.py.

Run:  uv run python scripts/noe/derive_pdf_hig_sources.py
      uv run python scripts/noe/derive_pdf_hig_sources.py --noe-dir output/noe
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.noe.pdf_hig_sources import derive_layer_files  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="NÖ-HiG-Quellobjekte aus den SekROP-750-m-Zonen rekonstruieren.")
    p.add_argument("--noe-dir", default="output/noe", help="Verzeichnis der pdf_750m_*.geojson")
    args = p.parse_args(argv)
    print("Rekonstruiere NÖ-HiG-Quellobjekte (Erosion 750−50 m, polylabel-Fallback) ...", flush=True)
    derive_layer_files(Path(args.noe_dir))
    print("Fertig.", flush=True)


if __name__ == "__main__":
    main()
