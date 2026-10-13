"""Prep Kataster, Stufe c: Streusiedlungs-/HiG-Kandidaten aus der DKM.

Schnitt (prep-Grenze): der DKM-Scan, den ``pipeline/layers/hig.py`` früher
selbst über das 5,3-GB-GeoParquet gefahren hat (``calc.hig_detection.
scan_dkm_candidates``), läuft jetzt einmal hier. Ergebnis, klein und
verlustfrei (GeoParquet EPSG:31287, Reihenfolge und Doppelwerte unverändert):

- ``streusiedlung_kandidaten.parquet``: Bauflächen-Footprints außerhalb des
  Widmungsfilters (inkl. 5-m-Scheibe für adressbehaftete Riesenflächen;
  adresslose entfallen) mit ``bundesland``, ``cx``/``cy``.
- ``streusiedlung_garten.parquet``: Garten-Punkte (``bundesland``, Punkt).
- ``streusiedlung_bericht.json``: Zählwerte und Parameter.

Hüllenbildung, BEV-Signale und Klassifikation bleiben in der Layer-Stufe.

Eingaben (alle aus derived/prep): Kataster-GeoParquet (Stufe b), Widmung,
NÖ-SekROP, BEV-Adressen und das DGM-Zielgitter. Der Filter nutzt die
Konstanten ``HIG_FILTER_BUFFER_M``/``HIG_MAX_FOOTPRINT_M2`` aus
``calc.abschichtung_common``. Zwischenstand-Fingerabdruck:
``derived/work/kataster/c_streusiedlung``.

Weitergabe: fehlt das große Kataster-GeoParquet, die beiden Produkte sind
aber da, wird übersprungen.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pipeline import contract, fingerprint, runtime

MODULE_PATH = Path(__file__)
WORK_DIR = contract.WORK["kataster"] / "c_streusiedlung"
# Rand um das Gitter, in dem Zentroide noch aufgenommen werden; die Layer-Stufe
# schneidet danach mit ihrem eigenen (kleineren) Rand nach.
SCAN_MARGIN_M = 5000.0


def _products() -> tuple[Path, Path, Path]:
    files = contract.PREP_FILES["kataster"]
    return (
        files["streusiedlung_kandidaten"],
        files["streusiedlung_garten"],
        contract.PREP_REPORT_FILES["kataster"]["streusiedlung_bericht"],
    )


def _inputs() -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    return sorted(
        [
            contract.PREP_FILES["kataster"]["at_dkm_gst_nfl"],
            *contract.PREP_FILES["widmung"].values(),
            *(
                contract.PREP_FILES["noe_sekrop"][n]
                for n in ("pdf_750m_geb", "pdf_750m_gwr", "pdf_750m_gruenland_widmung")
            ),
            contract.PREP_FILES["adressen"]["adressen"],
            contract.PREP_FILES["gelaende"]["dgm"],
            MODULE_PATH,
            root / "calc" / "hig_detection.py",
            root / "calc" / "hig_source_masks.py",
        ]
    )


def run(force: bool = False) -> Path:
    cand_path, garden_path, report_path = _products()
    source = contract.PREP_FILES["kataster"]["at_dkm_gst_nfl"]
    have = all(p.exists() for p in (cand_path, garden_path, report_path))

    if not force and have and not source.exists():
        print(
            "[skip]  prep-kataster-c: Produkt vorhanden, Kataster-GeoParquet fehlt – übersprungen",
            flush=True,
        )
        return cand_path.parent
    if not source.exists():
        raise SystemExit(
            f"[fehler] prep-kataster-c: {source} fehlt und die Streusiedlungs-Produkte fehlen. "
            "Kataster-Rohdaten (data/kataster/, siehe docs/rohdaten.md) bereitstellen und "
            "`make prep-kataster` ausführen."
        )
    inputs = _inputs()
    if not force and have and fingerprint.matches(WORK_DIR, inputs):
        print(f"[skip]  prep-kataster-c: Fingerabdruck unveraendert -> {cand_path.parent}", flush=True)
        return cand_path.parent

    # Schwere Importe erst hier (Skip-Pfade bleiben billig).
    from calc.abschichtung_common import (  # noqa: PLC0415
        HIG_FILTER_BUFFER_M,
        HIG_MAX_FOOTPRINT_M2,
        load_grid,
        timed,
    )
    from calc.bev_register import load_address_points  # noqa: PLC0415
    from calc.config import load_config  # noqa: PLC0415
    from calc.hig_detection import scan_dkm_candidates, write_candidate_scan  # noqa: PLC0415
    from calc.hig_source_masks import (  # noqa: PLC0415
        candidate_filter_mask,
        noe_pdf_mask,
        zoning_masks,
    )

    runtime.ensure_dir(cand_path.parent)
    runtime.ensure_dir(WORK_DIR)
    with timed("kataster-c: Gitter + Widmungsfilter"):
        cfg = load_config()
        grid = load_grid(cfg, None)
        zoning = zoning_masks(contract.PREP["widmung"], grid)
        noe_pdf = noe_pdf_mask(contract.PREP["noe_sekrop"], grid)
        filter_mask = candidate_filter_mask(zoning, noe_pdf, HIG_FILTER_BUFFER_M, grid)
        address_xy = load_address_points()
    with timed("kataster-c: DKM-Scan"):
        scan = scan_dkm_candidates(
            source, grid, filter_mask, HIG_MAX_FOOTPRINT_M2,
            margin_m=SCAN_MARGIN_M, address_xy=address_xy,
        )
    write_candidate_scan(
        scan, cand_path, garden_path, report_path,
        {
            "HIG_FILTER_BUFFER_M": HIG_FILTER_BUFFER_M,
            "HIG_MAX_FOOTPRINT_M2": HIG_MAX_FOOTPRINT_M2,
            "SCAN_MARGIN_M": SCAN_MARGIN_M,
        },
    )
    fingerprint.write(WORK_DIR, inputs)
    print(
        f"[done]  prep-kataster-c: {len(scan):,} Kandidaten, {len(scan.garden_xy):,} Garten-Punkte "
        f"-> {cand_path.parent}",
        flush=True,
    )
    return cand_path.parent


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
