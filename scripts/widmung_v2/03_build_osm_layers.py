"""OSM-Restlayer der Widmungs-Abschichtung v2 (Plan Phase 2, Skript 2 von 3).

Kette: build_official_zoning_layers.py -> build_hig_sources.py -> **dieses
Skript** -> create_widmung_v2_distance_zones.py.

Was v2 gegenüber v1 (scripts/main/build_widmung_osm_layers.py) ändert:

* **Kein OSM-Adress-Cluster-Pfad mehr.** Streusiedlungen kommen jetzt aus
  DKM-Bauflächen + BEV-Adressregister (build_hig_sources.py), nicht aus
  OSM-Adress-Ansammlungen, die zuletzt 84 % der Quellfläche stellten.
* **Kein Wien/Burgenland-OSM-Fallback.** Beide Bundesländer haben inzwischen
  amtliche Widmung (Burgenland seit Phase 0, Wien seit Juli 2026).

OSM liefert hier nur noch das, wofür es keine amtliche Quelle gibt:

  cableway_buildings_source    Gebäude nahe einer OSM-Aerialway-Linie (Liftstationen)
  general_buildings_source     alles übrige OSM-Gebäude (Garagen, Schuppen,
                               Ställe, Industrie, untypisiert) PLUS die bewohnten
                               Einzellagen aus build_hig_sources.py - 25 m
  + Infrastrukturmasken (ohne 380/400-kV: seit dem Clean-Schema kein
    Ausschlusskriterium mehr) und die neuen Flughafen-Korridorbänder
    (airport_area_major + airport_runway_corridor_5km, nur Hauptflughäfen)

Jedes OSM-Gebäude landet in GENAU EINER dieser beiden Kategorien, in dieser
Priorität, und nur wenn es nicht ohnehin schon von einer amtlichen Quelle
abgedeckt ist (Siedlung, Ferienhaus, HiG-Widmung, NÖ-PDF-Zone, Streusiedlungs-
Hülle, bewohnte Einzellage). Die frühere Kategorie important_objects_source
(Kirchen/Kapellen/Burgen/Ruinen + Friedhöfe) ist entfallen; die Gebäude laufen
als general_buildings mit, Friedhofsflächen sind kein Kriterium mehr.

Vorgeschaltet: Windkraftanlagen werden aus dem OSM-Gebäude-Layer entfernt
(drop_wind_power_buildings) - OSM taggt manche Anlagen zusätzlich mit
`building=yes`, sie würden sonst als general_buildings ihren eigenen Standort
ausschließen.

Run:  uv run python scripts/main/build_widmung_v2_layers.py
Checkpoints: output/abschichtung_widmung_v2/distance_layers/*.tif
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.config import load_config  # noqa: E402
from windkraft.calc.abschichtung_common import (  # noqa: E402
    BUILDING_CLASSIFICATION_REVISION,
    CABLEWAY_BUILDING_MATCH_RADIUS_M,
    OSM_PBF_COLUMNS,
    TARGET_CRS,
    admin_boundaries,
    build_airport_corridor_masks,
    build_infrastructure_masks,
    building_points,
    drop_wind_power_buildings,
    ensure_group_layers,
    expand_bounds,
    layer_path,
    load_grid,
    osm_layer_path,
    raster_mask,
    read_layer,
    read_layer_mask,
    sample_mask_at_points,
    timed,
)

# Von build_hig_sources.py geschriebene Quellen, die hier abgedeckte Flächen markieren.
# bewohnt_einzellage_source zählt mit: diese Gebäude haben schon ihr eigenes
# 25-m-Band und sollen nicht noch einmal als general_buildings klassifiziert werden.
OFFICIAL_COVER_LAYERS = [
    "official_settlement_source",
    "ferienhaus_tourismus_source",
    "official_hig_source",
    "noe_pdf_750m_zones",
    "hig_hulls_source",
    "bewohnt_einzellage_source",
]

OSM_LAYER_NAMES = [
    "cableway_buildings_source",
    "general_buildings_source",
]

# power_380_400kv fehlt bewusst: Stromleitungen sind seit dem Clean-Schema
# (Aug 2026) kein Ausschlusskriterium der v2-Kette mehr.
INFRA_LAYER_NAMES = [
    "road_motorway_trunk",
    "road_federal_state",
    "rail_main",
    "cableway_people_150m",
    "military_restricted_area",
]
AIRPORT_LAYER_NAMES = ["airport_area_major", "airport_runway_corridor_5km"]


def _require_hig_layers(layer_dir: Path) -> None:
    missing = [n for n in OFFICIAL_COVER_LAYERS if not layer_path(layer_dir, n).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing checkpoint(s) in {layer_dir}: {', '.join(missing)}. "
            "Run scripts/main/build_hig_sources.py first."
        )


def _official_cover_mask(layer_dir: Path, grid: dict) -> np.ndarray:
    mask = np.zeros(grid["shape"], dtype=bool)
    for name in OFFICIAL_COVER_LAYERS:
        mask |= read_layer_mask(layer_path(layer_dir, name))
    return mask


def _as_mask(gdf: gpd.GeoDataFrame, grid: dict, label: str) -> np.ndarray:
    if gdf.empty:
        return np.zeros(grid["shape"], dtype=bool)
    return raster_mask(gpd.GeoDataFrame(gdf, geometry="geometry", crs=TARGET_CRS), 0.0, grid, label)


def build_osm_building_sources(cfg: dict, grid: dict, args: argparse.Namespace) -> dict[str, np.ndarray]:
    """Zwei disjunkte OSM-Gebäudeklassen unter den amtlich nicht abgedeckten Gebäuden."""
    layer_dir = Path(args.layer_dir)
    _require_hig_layers(layer_dir)
    covered_mask = _official_cover_mask(layer_dir, grid)

    source_bounds = expand_bounds(grid["bounds"], CABLEWAY_BUILDING_MATCH_RADIUS_M)
    buildings = read_layer(
        osm_layer_path(cfg, args.osm_pbf, args.osm_pbf_cache_dir, "buildings", source_bounds),
        bounds=source_bounds, columns=OSM_PBF_COLUMNS["buildings"],
    )
    buildings = buildings[buildings.geometry.notnull() & ~buildings.geometry.is_empty].copy()

    # Windkraftanlagen raus, BEVOR eine der drei Kategorien greift: OSM trägt bei
    # einigen Anlagen `building=yes` auf derselben Way/Relation wie die
    # Generator-Tags, sie kämen sonst als general_buildings mit 25 m durch und
    # würden ihren eigenen Standort ausschließen (Repowering-Flächen!). Eigener
    # OSM-Layer statt Zusatz-Tags im buildings-Layer, weil osm_layer_path() nur
    # nach {pbf}_{layer} cached - siehe drop_wind_power_buildings().
    wind_power = read_layer(
        osm_layer_path(cfg, args.osm_pbf, args.osm_pbf_cache_dir, "windpower", source_bounds),
        bounds=source_bounds,
    )
    buildings = drop_wind_power_buildings(buildings, wind_power)

    aerialways = read_layer(
        osm_layer_path(cfg, args.osm_pbf, args.osm_pbf_cache_dir, "aerialways", source_bounds),
        bounds=source_bounds, columns=OSM_PBF_COLUMNS["aerialways"],
    )

    # Bewohnte Einzellagen (< 5 adressierte Objekte) und die Bauflächen der
    # NÖ-Streusiedlungs-Hüllen zählen zu den allgemeinen Gebäuden (25 m):
    # den 750-m-Schutz trägt in NÖ die amtliche SekROP-Quelle, der
    # Gebäude-Fußabdruck bleibt trotzdem ausgeschlossen.
    dkm_footprints = read_layer_mask(layer_path(layer_dir, "bewohnt_einzellage_source"))
    bl = admin_boundaries(cfg, grid["bounds"])
    noe = bl[bl["BL"].eq("Niederösterreich")] if "BL" in bl.columns else bl.iloc[0:0]
    if not noe.empty:
        noe_mask = raster_mask(noe[["geometry"]].copy(), 0.0, grid, "NÖ Landesfläche")
        dkm_footprints = dkm_footprints | (read_layer_mask(layer_path(layer_dir, "hig_hulls_source")) & noe_mask)

    zero = np.zeros(grid["shape"], dtype=bool)
    if buildings.empty:
        return {
            "cableway_buildings_source": zero,
            "general_buildings_source": dkm_footprints,
        }

    points = building_points(buildings)
    covered = sample_mask_at_points(covered_mask, points, grid)

    # 1) Seilbahngebäude: Restgebäude nahe einer Aerialway-Linie.
    remaining = ~covered
    cableway_proximity = raster_mask(aerialways, CABLEWAY_BUILDING_MATCH_RADIUS_M, grid, "cableway_proximity") if not aerialways.empty else zero
    is_cableway = remaining & sample_mask_at_points(cableway_proximity, points, grid)
    cableway_source = _as_mask(buildings.loc[is_cableway, ["geometry"]], grid, "cableway_buildings")

    # 2) Alles Übrige ist geringfügig/unklassifiziert - plus die DKM/BEV-
    #    Fußabdrücke (Einzellagen + NÖ-Streusiedlungs-Bauflächen). Hier landen
    #    seit dem Wegfall der Kategorie auch Kirchen/Kapellen/Burgen/Ruinen:
    #    weiterhin als Gebäude ausgeschlossen, aber ohne eigenen Abstand.
    is_general = remaining & (~is_cableway)
    general_source = _as_mask(buildings.loc[is_general, ["geometry"]], grid, "general_buildings_source") | dkm_footprints

    print(
        "[info]  v2 OSM-Gebäudeklassifikation: "
        f"osm_buildings={len(buildings):,}, amtlich_abgedeckt={int(covered.sum()):,}, "
        f"cableway={int(is_cableway.sum()):,}, "
        f"general={int(is_general.sum()):,} + dkm_fussabdruck_zellen={int(dkm_footprints.sum()):,}",
        flush=True,
    )
    return {
        "cableway_buildings_source": cableway_source,
        "general_buildings_source": general_source,
    }


def _cover_fingerprint(layer_dir: Path) -> str:
    """Content fingerprint of build_hig_sources.py's outputs, for checkpoint invalidation."""
    parts = []
    for name in OFFICIAL_COVER_LAYERS:
        p = layer_path(layer_dir, name)
        parts.append(f"{name}:{p.stat().st_mtime_ns}" if p.exists() else f"{name}:missing")
    return "|".join(parts)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OSM-Restlayer (wichtige Einzelobjekte, Seilbahnen, sonstige Gebäude) + Infrastruktur/Flughäfen für die Widmungs-Abschichtung v2.")
    p.add_argument("--config", default="config/config.json")
    p.add_argument("--layer-dir", default="output/abschichtung_widmung_v2/distance_layers", help="Geteilt mit build_hig_sources.py")
    p.add_argument("--bbox", default=None, help="EPSG:31287 bbox minx,miny,maxx,maxy für Smoke-Tests")
    p.add_argument("--mode", choices=["standard", "minimum"], default="standard",
                   help="Wird an build_infrastructure_masks() durchgereicht (angeschlossen), "
                        "ist aber wirkungslos mit dem heutigen Inhalt von INFRA_RULES "
                        "(abschichtung_common.py ~263-270): dort gilt für jede Regel "
                        "standard == minimum, es gibt also keinen Unterschied zwischen den "
                        "beiden Modi. Wirkung nur, falls INFRA_RULES künftig unterschiedliche "
                        "standard-/minimum-Werte bekommt.")
    p.add_argument("--total-height-m", type=float, default=250.0,
                   help="Wird an build_infrastructure_masks() durchgereicht (angeschlossen), "
                        "ist aber wirkungslos mit dem heutigen Inhalt von INFRA_RULES "
                        "(abschichtung_common.py ~263-270): keine Regel nutzt dort die "
                        "Höhen-Platzhalter \"h\"/\"max(h,100)\", alle Distanzen sind feste "
                        "Meterwerte. Wirkung nur, falls INFRA_RULES künftig eine höhenabhängige "
                        "Regel bekommt.")
    p.add_argument("--osm-pbf", default="data/austria-260330.osm.pbf")
    p.add_argument("--osm-pbf-cache-dir", default="output/abschichtung/osm_pbf_layers", help="Geteilt mit create_osm_wka_distance_zones.py (reiner Read-Through-Cache)")
    p.add_argument("--force-layers", action="store_true")
    p.add_argument("--skip-infra", action="store_true", help="Infrastruktur-/Flughafenmasken überspringen")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with timed("load config/grid"):
        cfg = load_config(args.config)
        grid = load_grid(cfg, args.bbox)
    layer_dir = Path(args.layer_dir)
    _require_hig_layers(layer_dir)

    # Die Revision muss mit in die Checkpoint-Tags: sonst gelten vorhandene
    # distance_layers/*.tif weiter als gültig und eine geänderte Klassifikation
    # (z. B. der WKA-Filter) würde stillschweigend nicht wirksam.
    extra_tags = {
        "HIG_SOURCE_FINGERPRINT": _cover_fingerprint(layer_dir),
        "BUILDING_CLASSIFICATION_REVISION": BUILDING_CLASSIFICATION_REVISION,
    }

    def _tags_ok(tags: dict) -> bool:
        return all(tags.get(k) == v for k, v in extra_tags.items())

    with timed("build/update checkpoint layers"):
        ensure_group_layers(
            layer_dir, OSM_LAYER_NAMES, "v2 OSM building classification",
            lambda: build_osm_building_sources(cfg, grid, args), grid, args.force_layers,
            extra_ok=_tags_ok, extra_tags=extra_tags,
        )
        if not args.skip_infra:
            ensure_group_layers(layer_dir, INFRA_LAYER_NAMES, "infrastructure masks", lambda: build_infrastructure_masks(cfg, grid, args), grid, args.force_layers)
            ensure_group_layers(layer_dir, AIRPORT_LAYER_NAMES, "airport corridor masks", lambda: build_airport_corridor_masks(cfg, grid, args), grid, args.force_layers)

    print(f"Checkpoint layers updated in {layer_dir}.")


if __name__ == "__main__":
    main()
