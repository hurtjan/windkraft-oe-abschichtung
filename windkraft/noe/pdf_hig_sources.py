"""Rekonstruiert die HiG-QUELLOBJEKTE aus den NÖ-SekROP-750-m-Zonen (TeilC 3.2).

Das PDF enthält laut seinen OCG-Layernamen nur die fertig gepufferten,
dissolveten Zonen (``Widmung_GEB_…_Puffer_750m_Diss``,
``Wohngeb_GWR_NotInWiHue2021_Puffer_750m_Diss``,
``Widmung_Gkg_Gc_Gho_…_Puffer_750m``) — die Quellobjekte selbst wurden nie
mitexportiert. Die Morphologie liefert sie trotzdem zurück: für eine Zone
Z = S (+) D750 gilt

    Z (-) D(750-δ)             ⊇  S (+) Dδ        (keine Quelle geht verloren)
    (Z (-) D(750-δ)) (+) D750  ⊆  Z (+) Dδ        (Re-Puffer ⊆ Zone + δ)

d. h. die Erosion um 750−δ enthält jede Quelle, und der einheitliche
750-m-Puffer der Pipeline reproduziert die amtliche Zone bis auf höchstens
δ nach außen (δ = 50 m = 2 Rasterzellen, konservative Richtung).

Sonderfälle:
  * Komponenten < 1 ha sind Extraktions-Slivers (Füllfarben-Artefakte,
    kleinste Bounding-Box im PDF 0,06 pt²) — echte Zonen sind ≥ ~176 ha
    (Kreis r=750). Sie werden verworfen und gezählt.
  * An der Landesgrenze geclippte Zonen können bei der Erosion leerlaufen;
    dann ersetzt der Pol der Unzugänglichkeit (polylabel, tiefster
    Innenpunkt) ⊕ δ die Quelle.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import shapely
from shapely.geometry.base import BaseGeometry
from shapely.ops import polylabel

ZONE_BUFFER_M = 750.0
ERODE_DELTA_M = 50.0
MIN_ZONE_COMPONENT_M2 = 10_000.0  # 1 ha: weit über Sliver-, weit unter Zonengröße
POLYLABEL_TOL_M = 5.0

# Zonen-Layer (Objekt + 750 m, aus extract_noe_vector_layers.py) -> Quell-Layer.
ZONE_TO_SOURCE_LAYERS = {
    "pdf_750m_geb": "pdf_hig_source_geb",
    "pdf_750m_gwr": "pdf_hig_source_gwr",
    "pdf_750m_gruenland_widmung": "pdf_hig_source_gruenland_widmung",
}

NOE_PDF_SOURCE_LAYER_NAMES = tuple(ZONE_TO_SOURCE_LAYERS.values())


def derive_source_geoms(zone_geoms: list[BaseGeometry]) -> tuple[list[BaseGeometry], dict]:
    """Erodiert jede Zonen-Komponente um 750−δ m; Fallback: polylabel ⊕ δ."""
    sources: list[BaseGeometry] = []
    stats = {"n_components": 0, "n_eroded": 0, "n_fallback": 0,
             "n_dropped": 0, "dropped_m2": 0.0}
    for geom in zone_geoms:
        for comp in shapely.get_parts(shapely.make_valid(geom)):
            if comp.is_empty or comp.geom_type != "Polygon":
                continue
            stats["n_components"] += 1
            if comp.area < MIN_ZONE_COMPONENT_M2:
                stats["n_dropped"] += 1
                stats["dropped_m2"] += comp.area
                continue
            eroded = comp.buffer(-(ZONE_BUFFER_M - ERODE_DELTA_M))
            if eroded.is_empty:
                stats["n_fallback"] += 1
                sources.append(polylabel(comp, tolerance=POLYLABEL_TOL_M).buffer(ERODE_DELTA_M))
            else:
                stats["n_eroded"] += 1
                sources.append(eroded)
    return sources, stats


def roundtrip_report(zone_geoms: list[BaseGeometry], source_geoms: list[BaseGeometry]) -> dict:
    """Prüft Quelle ⊕ 750 m gegen die Original-Zonen (Flächen in m²)."""
    zones = shapely.union_all([shapely.make_valid(g) for g in zone_geoms])
    if not source_geoms:
        return {"zone_m2": zones.area, "rebuffer_m2": 0.0,
                "uncovered_m2": zones.area, "extra_m2": 0.0}
    rebuffered = shapely.union_all(source_geoms).buffer(ZONE_BUFFER_M)
    return {
        "zone_m2": zones.area,
        "rebuffer_m2": rebuffered.area,
        "uncovered_m2": zones.difference(rebuffered).area,
        "extra_m2": rebuffered.difference(zones).area,
    }


def derive_layer_files(noe_dir: Path) -> None:
    """Liest pdf_750m_*.geojson und schreibt pdf_hig_source_*.geojson (+_wgs84)."""
    for zone_name, source_name in ZONE_TO_SOURCE_LAYERS.items():
        zone_path = noe_dir / f"{zone_name}.geojson"
        if not zone_path.exists():
            raise FileNotFoundError(
                f"Zonen-Layer fehlt: {zone_path}. "
                "Erst scripts/noe/extract_noe_vector_layers.py ausführen."
            )
        zones = gpd.read_file(zone_path)
        source_geoms, stats = derive_source_geoms(list(zones.geometry))
        out = gpd.GeoDataFrame(geometry=source_geoms, crs=zones.crs)
        out["area_ha"] = (out.geometry.area / 1e4).round(3)
        out.to_file(noe_dir / f"{source_name}.geojson", driver="GeoJSON")
        out.to_crs("EPSG:4326").to_file(noe_dir / f"{source_name}_wgs84.geojson", driver="GeoJSON")

        rt = roundtrip_report(list(zones.geometry), source_geoms)
        print(
            f"  [{source_name}] {stats['n_components']} Zonen-Komponenten -> "
            f"{stats['n_eroded']} erodiert + {stats['n_fallback']} polylabel-Fallback, "
            f"{stats['n_dropped']} Slivers verworfen ({stats['dropped_m2'] / 1e4:.2f} ha); "
            f"Quellen {out.geometry.area.sum() / 1e6:.1f} km²",
            flush=True,
        )
        print(
            f"    Roundtrip ⊕750 m: Zone {rt['zone_m2'] / 1e6:.1f} km², "
            f"unabgedeckt {rt['uncovered_m2'] / 1e6:.3f} km² "
            f"({100 * rt['uncovered_m2'] / max(rt['zone_m2'], 1):.3f} %), "
            f"Überstand {rt['extra_m2'] / 1e6:.3f} km² "
            f"({100 * rt['extra_m2'] / max(rt['zone_m2'], 1):.3f} %)",
            flush=True,
        )
