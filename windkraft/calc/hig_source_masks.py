"""Rastermasken der amtlichen HiG-Quellen (Stufe A der Erkennung).

Aus scripts/main/build_hig_sources.py extrahiert, damit Parameter-Experimente
(z. B. der Streusiedlungs-Sweep) exakt denselben Kandidatenfilter verwenden wie
die Pipeline - eine zweite Implementierung würde bei der nächsten Quellenänderung
lautlos auseinanderlaufen.

Alle Funktionen arbeiten auf dem 25-m-Lattice (``grid`` aus ``load_grid``).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from windkraft.calc.abschichtung_common import (
    admin_boundaries,
    raster_mask,
    read_layer,
    uniform_buffer_cell_mask,
)

FERIENHAUS_CATEGORY = "ferienhaus_tourismus"

NOE_PDF_LAYER_NAMES = ("pdf_750m_geb", "pdf_750m_gwr", "pdf_750m_gruenland_widmung")

# Rekonstruierte QUELLOBJEKTE hinter den Zonen (windkraft/noe/pdf_hig_sources.py):
# das PDF exportiert nur die dissolveten 750-m-Puffer, die Quellen entstehen per
# Erosion um 750−δ. Diese Layer werden von der Pipeline normal mit 750 m gepuffert.
NOE_PDF_SOURCE_LAYER_NAMES = (
    "pdf_hig_source_geb",
    "pdf_hig_source_gwr",
    "pdf_hig_source_gruenland_widmung",
)


def zoning_masks(zoning_dir: Path, grid: dict) -> dict[str, np.ndarray]:
    """Rasterisierte Widmungs-Buckets: Siedlung, Ferienhaus, HiG-Rest, Industrie."""
    bounds = grid["bounds"]
    wohn = read_layer(zoning_dir / "wohn_misch_combined.gpkg", bounds=bounds)
    hig = read_layer(zoning_dir / "haeuser_im_gruenen_combined.gpkg", bounds=bounds)
    industrie = read_layer(zoning_dir / "industrie_negativ_combined.gpkg", bounds=bounds)

    if "category" in hig.columns:
        is_ferienhaus = hig["category"].eq(FERIENHAUS_CATEGORY)
        ferienhaus, hig_rest = hig[is_ferienhaus], hig[~is_ferienhaus]
    else:
        ferienhaus, hig_rest = hig.iloc[0:0], hig

    return {
        "official_settlement_source": raster_mask(wohn, 0.0, grid, "official_settlement"),
        "ferienhaus_tourismus_source": raster_mask(ferienhaus, 0.0, grid, "ferienhaus_tourismus"),
        "official_hig_source": raster_mask(hig_rest, 0.0, grid, "official_hig"),
        "industrie_negativ": raster_mask(industrie, 0.0, grid, "industrie_negativ"),
    }


def noe_pdf_layer_masks(noe_dir: Path, grid: dict) -> dict[str, np.ndarray]:
    """Die drei SekROP-750-m-Klassen einzeln (für Validierung gegen die GWR-Klasse)."""
    out = {}
    for name in NOE_PDF_LAYER_NAMES:
        path = noe_dir / f"{name}.geojson"
        if not path.exists():
            print(f"[warn]  NÖ-PDF-Zone fehlt: {path}", flush=True)
            out[name] = np.zeros(grid["shape"], dtype=bool)
            continue
        zones = read_layer(path, bounds=grid["bounds"])
        out[name] = raster_mask(zones, 0.0, grid, name)
    return out


def noe_pdf_mask(noe_dir: Path, grid: dict) -> np.ndarray:
    """Vereinigung der SekROP-Klassen. Bereits Objekt + Puffer - nie nachpuffern."""
    mask = np.zeros(grid["shape"], dtype=bool)
    for layer in noe_pdf_layer_masks(noe_dir, grid).values():
        mask |= layer
    return mask


def noe_pdf_source_mask(noe_dir: Path, grid: dict) -> np.ndarray:
    """Rekonstruierte SekROP-Quellobjekte; werden im Aggregat 750 m gepuffert.

    Fehlende Dateien sind ein harter Fehler: ein leeres NÖ-Quellband würde
    lautlos einen Großteil des NÖ-Ausschlusses entfernen.
    """
    mask = np.zeros(grid["shape"], dtype=bool)
    for name in NOE_PDF_SOURCE_LAYER_NAMES:
        path = noe_dir / f"{name}.geojson"
        if not path.exists():
            raise FileNotFoundError(
                f"NÖ-PDF-Quellobjekte fehlen: {path}. Erst "
                "`uv run --extra pdf python scripts/noe/extract_noe_vector_layers.py` ausführen "
                "(ruft derive_layer_files() selbst auf)."
            )
        sources = read_layer(path, bounds=grid["bounds"])
        mask |= raster_mask(sources, 0.0, grid, name)
    return mask


def widmung_seed(zoning: dict[str, np.ndarray]) -> np.ndarray:
    """Vereinigung der drei Widmungs-Buckets, die Gebäude "amtlich erfassen"."""
    return (
        zoning["official_settlement_source"]
        | zoning["official_hig_source"]
        | zoning["ferienhaus_tourismus_source"]
    )


def candidate_filter_mask(
    zoning: dict[str, np.ndarray],
    noe_pdf: np.ndarray | None,
    filter_buffer_m: float,
    grid: dict,
) -> np.ndarray:
    """Stufe-A-Filter: Gebäude innerhalb gelten als von der Widmung erfasst.

    ``noe_pdf`` ist optional, damit Validierungsläufe (z. B. der NÖ-Vergleich
    gegen die SekROP-Zonen selbst) die Zonen gezielt weglassen können.
    """
    mask = uniform_buffer_cell_mask(widmung_seed(zoning), filter_buffer_m, grid, "hig_filter")
    if noe_pdf is not None:
        mask = mask | noe_pdf
    return mask
