"""Streusiedlungs-Erkennung: Parameter-Varianten über den HiG-Kandidaten.

Idee: statt jedes bewohnte Einzelobjekt (v2-Regel) nur *Gebiete* erkennen, in
denen mehrere verstreute, adressierte Objekte nahe beieinander liegen. Zwei
Stellschrauben:

* **Verkettungsdistanz** ``chain_m`` - bis zu welchem Abstand zählen Objekte
  als EIN Gebiet (v2: 150 m; Streusiedlungs-Kandidat: eher 300-400 m).
* **Adress-Schwelle** - Mindestzahl adressierter Objekte je Hülle (v2: 1).

Der teure Teil (DKM-Scan, BEV-Signale) hängt an KEINER der beiden Schrauben:
``building_signals`` ist je Gebäude, die Schwelle ist nur ein Filter auf den
aggregierten Hüllen-Kennzahlen. Ein Sweep rechnet den Scan deshalb einmal und
bildet dann je Verkettungsdistanz neue Hüllen (``chain_variant``); alle
Schwellen darüber sind gratis.

Als Referenzmaßstab dient Niederösterreich: die SekROP-750-m-Zonen (GWR-Klasse
= amtliches Bewohnt-Signal) sind faktisch eine amtliche Streusiedlungs-
Ausweisung. ``noe_reference_masks`` liefert die Masken für einen Lauf, der die
Erkennung OHNE den PDF-Filter gegen genau diese Zonen misst.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import contract
from calc.abschichtung_common import (
    HIG_ADDRESS_RADIUS_M,
    HIG_GARDEN_RADIUS_M,
    timed,
    uniform_buffer_cell_mask,
)
from calc.bev_register import load_address_points, load_building_points
from calc.hig_detection import (
    HULL_CLASS_BEWOHNT,
    aggregate_hulls,
    build_hulls,
    building_signals,
    dominant_bundesland,
    hull_polygons,
    label_mask,
    sample_labels,
    load_candidate_scan,
)
from calc.hig_source_masks import (
    zoning_masks,
)

# Saum, den die Erosion um jedes Gebäude stehen lässt (v2: dilate 75 - erode 40).
# Konstant gehalten, damit Varianten nur die VERKETTUNG ändern, nicht die Randbreite.
CHAIN_MARGIN_M = 35.0

# Verkettungsdistanzen und Adress-Schwellen des Standard-Sweeps.
DEFAULT_CHAINS_M = (150.0, 250.0, 350.0, 500.0)
DEFAULT_THRESHOLDS = (1, 3, 5, 8, 12)

# Puffer, mit dem eine erkannte Streusiedlungs-Hülle in die Abschichtung einginge.
STREUSIEDLUNG_BUFFER_M = 750.0


def chain_hull_params(chain_m: float) -> tuple[float, float]:
    """Verkettungsdistanz -> (dilate_m, erode_m) für build_hulls."""
    dilate = float(chain_m) / 2.0
    erode = max(dilate - CHAIN_MARGIN_M, 5.0)
    return dilate, erode


def load_candidate_signals(
    cfg: dict,
    grid: dict,
    *,
    zoning_dir: Path,
    noe_dir: Path,
    address_parquet: Path | None = None,
    building_parquet: Path | None = None,
    include_noe_pdf: bool,
    bl_filter: set[str] | None,
    max_chain_m: float,
) -> tuple[dict, np.ndarray, object, pd.DataFrame]:
    """Stufe A + DKM-Scan + BEV-Signale - der von allen Analysen geteilte teure Teil.

    Rückgabe: (zoning-Masken, CandidateScan, Signale je Gebäude).
    ``include_noe_pdf=False`` ist nicht mehr möglich (Filter im Prep-Produkt fest).
    """
    zoning = zoning_masks(Path(zoning_dir), grid)
    if not include_noe_pdf:
        raise ValueError(
            "include_noe_pdf=False wird nicht mehr unterstützt: der DKM-Scan liegt "
            "als Prep-Produkt (prep-kataster Stufe c) mit NÖ-PDF-Filter vor."
        )
    with timed("Kandidaten (Prep-Produkt)"):
        files = contract.PREP_FILES["kataster"]
        scan = load_candidate_scan(
            files["streusiedlung_kandidaten"], files["streusiedlung_garten"],
            contract.PREP_REPORT_FILES["kataster"]["streusiedlung_bericht"], grid,
            bl_filter=bl_filter, margin_m=chain_hull_params(max_chain_m)[0],
        )
        print(f"[info]  Kandidaten: {len(scan):,} von {scan.n_buildings_total:,} Bauflächen", flush=True)
    with timed("BEV-Signale"):
        address_xy = load_address_points(address_parquet)
        bev = load_building_points(building_parquet)
        signals = building_signals(
            scan, address_xy, bev, HIG_ADDRESS_RADIUS_M, HIG_GARDEN_RADIUS_M,
            industrie_widmung_mask=zoning["industrie_negativ"], grid=grid,
        )
    return zoning, scan, signals


def chain_variant(
    scan,
    signals: pd.DataFrame,
    grid: dict,
    chain_m: float,
    wohnanteil_min_share: float,
    industrie_widmung_min_share: float,
) -> dict:
    """Bewohnte Hüllen für EINE Verkettungsdistanz (Klassifikation wie v2).

    Rückgabe-Dict: ``polygone`` (GeoDataFrame nur der bewohnten Hüllen),
    ``labels``/``n_labels`` (für Puffer-Masken), ``n_hullen_gesamt``.
    """
    dilate, erode = chain_hull_params(chain_m)
    hull_mask, labels, n_labels = build_hulls(
        scan.geometries, grid, dilate, erode, label=f"chain{int(chain_m)}"
    )
    hull_label = sample_labels(labels, scan.centroids, grid)
    frame = aggregate_hulls(
        hull_label, signals, n_labels, wohnanteil_min_share, industrie_widmung_min_share
    )
    polys = hull_polygons(labels, hull_mask, frame, grid)
    if not polys.empty:
        polys["bundesland"] = dominant_bundesland(
            hull_label, scan.bundesland, polys["label"].to_numpy()
        )
    bewohnt = polys[polys["klasse"].eq(HULL_CLASS_BEWOHNT)].reset_index(drop=True)
    return {
        "chain_m": float(chain_m),
        "polygone": bewohnt,
        "labels": labels,
        "n_labels": n_labels,
        "n_huellen_gesamt": int(n_labels),
    }


def threshold_subset(bewohnt: pd.DataFrame, min_adressen: int, min_garten: int = 0) -> pd.DataFrame:
    """Hüllen, die die Streusiedlungs-Schwellen erfüllen."""
    keep = bewohnt["n_adressen"] >= int(min_adressen)
    if min_garten > 0:
        keep &= bewohnt["n_garten"] >= int(min_garten)
    return bewohnt[keep]


def subset_buffer_mask(
    variant: dict, subset: pd.DataFrame, buffer_m: float, grid: dict, label: str
) -> np.ndarray:
    """Zellmaske "Hüllen der Auswahl ⊕ buffer_m" - die Ausschlusswirkung der Variante."""
    mask = label_mask(variant["labels"], subset["label"].to_numpy(), variant["n_labels"])
    if buffer_m <= 0 or not mask.any():
        return mask
    return uniform_buffer_cell_mask(mask, buffer_m, grid, label)


def summarize_combo(chain_m: float, thr: int, subset: pd.DataFrame) -> dict:
    """Kennzahlen einer (Verkettung, Schwelle)-Kombination für die Sweep-Tabelle."""
    row = {
        "chain_m": int(chain_m),
        "min_adressen": int(thr),
        "n_huellen": int(len(subset)),
        "flaeche_km2": round(float(subset["area_ha"].sum()) / 100.0, 1),
        "median_ha": round(float(subset["area_ha"].median()), 2) if len(subset) else 0.0,
        "mittel_adressen": round(float(subset["n_adressen"].mean()), 1) if len(subset) else 0.0,
    }
    if "bundesland" in subset.columns:
        counts = subset["bundesland"].value_counts()
        for bl_name, n in counts.items():
            if bl_name:
                row[f"n_{bl_name}"] = int(n)
    return row


def noe_reference_masks(zoning: dict[str, np.ndarray], noe_pdf_layers: dict[str, np.ndarray],
                        grid: dict,
                        settlement_buffer_m: float = 1200.0,
                        hig_buffer_m: float = 750.0) -> dict[str, np.ndarray]:
    """Masken für den NÖ-Vergleich gegen die amtlichen SekROP-Zonen.

    ``fair``   Bereich, in dem allein die Hüllen-Erkennung liefern muss - also
               außerhalb dessen, was Siedlungs-/HiG-/Ferienhaus-Widmung in der
               echten Pipeline ohnehin abdecken (NÖ: 1.200 m Siedlung, 750 m Rest).
    ``ziel``   amtliche GWR-Zonen (bewohnte Objekte + 750 m) im fairen Bereich.
    ``amtlich_alle``  alle drei PDF-Klassen - was darüber hinausgeht, ist
               "Zusatzausschluss ohne amtliches Gegenstück".
    """
    covered = uniform_buffer_cell_mask(
        zoning["official_settlement_source"], settlement_buffer_m, grid, "noe_ref_siedlung"
    )
    for key in ("official_hig_source", "ferienhaus_tourismus_source"):
        if zoning[key].any():
            covered |= uniform_buffer_cell_mask(zoning[key], hig_buffer_m, grid, f"noe_ref_{key}")
    fair = ~covered

    amtlich_alle = np.zeros(grid["shape"], dtype=bool)
    for mask in noe_pdf_layers.values():
        amtlich_alle |= mask
    return {
        "fair": fair,
        "ziel": noe_pdf_layers["pdf_750m_gwr"] & fair,
        "amtlich_alle": amtlich_alle,
    }


def noe_validation_row(chain_m: float, thr: int, ours: np.ndarray,
                       reference: dict[str, np.ndarray], cell_km2: float) -> dict:
    """Abdeckungs-/Zusatzmetriken einer Kombination gegen die NÖ-Referenz."""
    ziel, fair, amtlich = reference["ziel"], reference["fair"], reference["amtlich_alle"]
    ziel_cells = int(ziel.sum())
    covered = int((ours & ziel).sum())
    extra = int((ours & fair & ~amtlich).sum())
    return {
        "chain_m": int(chain_m),
        "min_adressen": int(thr),
        "abdeckung_gwr_pct": round(100.0 * covered / max(ziel_cells, 1), 1),
        "verfehlt_km2": round((ziel_cells - covered) * cell_km2, 1),
        "zusatz_km2": round(extra * cell_km2, 1),
        "ausschluss_km2": round(int((ours & fair).sum()) * cell_km2, 1),
    }
