"""Finales GeoTIFF der Widmungs-Abschichtung v2 (Plan Phase 2, Skript 3 von 3).

Kette: build_official_zoning_layers.py -> build_hig_sources.py ->
build_widmung_v2_layers.py -> **dieses Skript**.

Puffer-Logik (Clean-Schema Aug 2026), Kernprinzip: **voller Siedlungsabstand
nur für amtlich gewidmetes Wohnbauland; alles andere Bewohnte einheitlich
750 m über die Häuser-im-Grünen-Familie.**

  settlement_buffer             Siedlungsabstand um amtliches Wohn-/Misch-/
                                Kern-/Dorfgebiet (alle 9 BL): NÖ 1.200 m,
                                sonst einheitlich 1.000 m
  haeuser_im_gruenen            Aggregat der HiG-Familie. 750 m um das
                                Bewohnte: haeuser_im_gruenen_ferienhaus
                                (Ferienhaus-/Tourismuswidmung), _widmung
                                (amtliche HiG-Widmung), _streusiedlung
                                (bewohnte Hüllen mit >= 5 adressierten
                                Objekten, 200-m-Verkettung). _streusiedlung
                                und _widmung laufen OHNE NÖ - dort definiert
                                allein die amtliche SekROP-Quelle den
                                750-m-Abstand. Die NÖ-PDF-Zonen (_noe_pdf)
                                sind schon Objekt + 750 m und fließen
                                ungepuffert ein.
  nonresidential_hulls_buffer   25 m - industriegebietartige und unbewohnte
                                Hüllen (Almen, Ställe, Betriebsareale)
  cableway_buildings_buffer     50 m - Liftstationen
  general_buildings_buffer      25 m - sonstige OSM-Gebäude PLUS bewohnte
                                Einzellagen (< 5 adressierte Objekte, vorher
                                eigenes 25-m-Bandpaar; Politikentscheidung
                                Gebiets- statt Einzelobjekt-Schutz bleibt)

Nicht mehr im Schema: haeuser_im_gruenen_wichtige_objekte (Kirchen/Kapellen/
Burgen/Klöster/Ruinen + Friedhöfe - Denkmal-/Ortsbildschutz ist kein
Immissionsabstand; die Gebäude laufen als general_buildings mit 25 m mit),
power_380_400kv (Stromleitungen
komplett entfernt), airport_area + airport_lateral_check_6km (ersetzt durch
airport_area_major + airport_runway_corridor_5km: nur die Hauptflughäfen aus
config buffers.major_airport_osm_ids, je Landebahn-Ende ein 5-km-Sektor ±15°
um die verlängerte Bahnachse), Siedlungsvarianten standardmäßig aus.

Nature-/Geography-/Windzonen-Masken sind unverändert aus
create_osm_wka_distance_zones.py übernommen. Zusätzlich (nur v2):

  geography_water_bodies        Größere Wasserkörper (Seen, Stauseen, Flüsse)
                                aus OSM (natural=water, waterway=riverbank,
                                landuse=reservoir) - Fußabdruck ohne Abstand,
                                Schwelle WATER_MIN_AREA_HA auf verbundene
                                Rasterflächen; zählt zu exclusion_geography

  available_blur_sigma_{100,200,250,300}m
                                Gauß-verschmierte Eignungsfläche (uint8 0-100)
                                als räumliche Unsicherheit der Zonengrenzen -
                                aus available_after_all_exclusions_raw (seit
                                Aug 2026; vorher available_cleaned), Sigma in
                                Metern - zeigt auch Splitter unter 10 ha

  wka_bestand_ausserhalb_zonen  Referenz, kein Ausschluss: bestehende Windräder
                                (OSM) außerhalb der amtlichen Windzonen, zu
                                Park-Hüllen verkettet (WKA_CLUSTER_CHAIN_M,
                                konvexe Hülle + WKA_HULL_MARGIN_M Rand)

Output: output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif
(bewusst ein eigener Ordner - die v1-Pipeline unter output/abschichtung_widmung/
bleibt unangetastet und weiter lauffähig)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.ops import unary_union

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.config import load_config  # noqa: E402
from windkraft.calc.abschichtung_common import (  # noqa: E402
    AIRPORT_CORRIDOR_HALF_ANGLE_DEG,
    AIRPORT_CORRIDOR_LENGTH_M,
    CABLEWAY_BUILDING_BUFFER_M,
    HIG_CHAIN_M,
    HIG_FAMILY_BUFFER_M,
    HIG_MIN_ADRESSEN,
    GENERAL_BUILDING_BUFFER_M,
    GEOGRAPHY_BANDS,
    NATURE_BANDS,
    NONRESIDENTIAL_HULL_BUFFER_M,
    OFFICIAL_ZONING_BANDS,
    SETTLEMENT_BUFFER_BY_BL,
    SETTLEMENT_BUFFER_VARIANTS,
    TARGET_CRS,
    UNCERTAINTY_BLUR_SIGMAS_M,
    WATER_BANDS,
    WATER_MIN_AREA_HA,
    admin_boundaries,
    building_points,
    build_geography_masks,
    build_nature_masks,
    build_official_zoning_masks,
    build_valid_area_mask,
    build_water_masks,
    compose_exclusion_geotiff,
    ensure_group_layers,
    expand_bounds,
    layer_path,
    load_grid,
    osm_layer_path,
    province_buffer_cell_mask,
    raster_mask,
    read_layer,
    read_layer_mask,
    resolve_variant_buffers,
    sample_mask_at_points,
    timed,
    uniform_buffer_cell_mask,
)

PIPELINE_TAG = "widmung_v2"
SETTLEMENT_VARIANT_SOURCE_BAND = "settlement_buffer"
# Ins extra_ok/extra_tags der abgeleiteten Checkpoint-Gruppen: ein Bump
# erzwingt deren Neubau, auch wenn die Quell-Checkpoints unverändert sind.
BAND_SCHEMA = "clean-38-ohne-wichtige-objekte-aug-2026"

# Bestands-WKA-Referenzband: Windräder außerhalb der amtlichen Zonen werden zu
# Park-Hüllen verkettet. 750 m Verkettung deckt übliche Anlagenabstände in
# österreichischen Parks (350-600 m) ab; der Rand entspricht grob Rotorradius
# plus Manövrierfläche.
WKA_BESTAND_BAND = "wka_bestand_ausserhalb_zonen"
WKA_CLUSTER_CHAIN_M = 750.0
WKA_HULL_MARGIN_M = 200.0


@dataclass(frozen=True)
class Band:
    name: str
    description: str


BANDS = [
    Band("official_settlement_source", "Amtliches Wohn-/Misch-/Kern-/Dorfgebiet, alle 9 Bundesländer (build_official_zoning_layers.py)"),
    Band("settlement_buffer", "Siedlungsabstand um official_settlement_source (NÖ 1.200 m, sonst 1.000 m)"),
    Band("haeuser_im_gruenen_ferienhaus", "HiG-Familie: Ferienhaus-/Tourismusgebiete (B 10030/10007/10017, T Tourismusgebiet § 40 (4))"),
    Band("haeuser_im_gruenen_widmung", "HiG-Familie: amtliche Häuser-im-Grünen-Widmung (Hofstellen, Camping, Golf, Kleingarten, Auffüllungsgebiete); ohne NÖ - dort trägt die PDF-Grünland-Klasse den Abstand"),
    Band("haeuser_im_gruenen_streusiedlung", "HiG-Familie: bewohnte Streusiedlungs-Hüllen (>= 5 adressierte Objekte, 200-m-Verkettung); ohne NÖ - dort gilt die amtliche PDF-Quelle"),
    Band("haeuser_im_gruenen_noe_pdf", "HiG-Familie: NÖ-SekROP-750-m-Zonen (Gebäude/GWR/Grünland-Widmung) - enthalten den 750-m-Puffer bereits"),
    Band("haeuser_im_gruenen", "Aggregat: 750 m um Ferienhaus + Widmung + Streusiedlung, vereinigt mit den NÖ-PDF-Zonen"),
    Band("nonresidential_hulls_source", "Industriegebietartige und unbewohnte DKM-Hüllen"),
    Band("nonresidential_hulls_buffer", "25 m um nonresidential_hulls_source (praktisch nur der Fußabdruck)"),
    Band("cableway_buildings_source", "OSM-Gebäude nahe einer Aerialway-Linie (Liftstationen etc.)"),
    Band("cableway_buildings_buffer", "50 m um cableway_buildings_source"),
    Band("general_buildings_source", "Übrige OSM-Gebäude (Garagen, Schuppen, Ställe, Industrie, untypisiert) + bewohnte Einzellagen und NÖ-Streusiedlungs-Bauflächen (DKM/BEV)"),
    Band("general_buildings_buffer", "25 m um general_buildings_source (praktisch nur der Fußabdruck)"),
    Band("road_motorway_trunk", "150 m buffer around motorway/trunk roads, tunnels excluded"),
    Band("road_federal_state", "150 m buffer around primary/secondary/tertiary roads, tunnels excluded"),
    Band("rail_main", "150 m buffer around normal/narrow-gauge railway, tunnels excluded"),
    Band("cableway_people_150m", "150 m buffer around OSM people-carrying aerialways/lifts"),
    Band("military_restricted_area", "OSM military/landuse=military area polygons rasterized without extra buffer"),
    Band("airport_area_major", "Areal der Hauptflughäfen (config buffers.major_airport_osm_ids), OSM-Aerodrome-Polygone ohne Zusatzpuffer"),
    Band("airport_runway_corridor_5km", "An-/Abflugkorridore der Hauptflughäfen: 5 km ab beiden Landebahn-Enden, ±15° um die verlängerte Bahnachse"),
    Band("nature_protection_areas", "Official protection areas: NP, NSG, ESG/Natura2000, Ramsar"),
    Band("osm_nature_protection_areas", "OSM protected/nature areas"),
    Band("geography_slope_too_steep", "Slope above configured exclusion threshold"),
    Band("geography_elevation_too_high", "Elevation above configured exclusion threshold"),
    Band("geography_wind_too_low", "Power density below configured wind threshold"),
    Band("geography_water_bodies", "Größere Wasserkörper (Seen/Stauseen/Flüsse) aus OSM, verbundene Flächen >= WATER_MIN_AREA_HA"),
]

HUMAN_BANDS = [
    "settlement_buffer",
    "haeuser_im_gruenen",
    "nonresidential_hulls_buffer",
    "cableway_buildings_buffer",
    "general_buildings_buffer",
    "road_motorway_trunk",
    "road_federal_state",
    "rail_main",
    "cableway_people_150m",
    "military_restricted_area",
    "airport_area_major",
    "airport_runway_corridor_5km",
]

# Abgeleitete HiG-Quellbänder: umbenannte/gefilterte Sichten auf die von
# build_hig_sources.py + build_widmung_v2_layers.py geschriebenen Checkpoints.
HIG_FAMILY_SOURCE_BANDS = [
    "haeuser_im_gruenen_ferienhaus",
    "haeuser_im_gruenen_widmung",
    "haeuser_im_gruenen_streusiedlung",
    "haeuser_im_gruenen_noe_pdf",
]

BUFFER_BANDS = [
    "settlement_buffer",
    "haeuser_im_gruenen",
    "nonresidential_hulls_buffer",
    "cableway_buildings_buffer",
    "general_buildings_buffer",
]

# Quell-Checkpoints, die build_hig_sources.py + build_widmung_v2_layers.py
# bereits geschrieben haben müssen.
REQUIRED_SOURCE_LAYERS = [
    "official_settlement_source",
    "ferienhaus_tourismus_source",
    "official_hig_source",
    "hig_hulls_source",
    "noe_pdf_750m_zones",
    "nonresidential_hulls_source",
    "cableway_buildings_source",
    "general_buildings_source",
    "road_motorway_trunk",
    "road_federal_state",
    "rail_main",
    "cableway_people_150m",
    "military_restricted_area",
    "airport_area_major",
    "airport_runway_corridor_5km",
]


def active_variants(enabled: bool) -> dict:
    return dict(SETTLEMENT_BUFFER_VARIANTS) if enabled else {}


def _check_required_sources(layer_dir: Path) -> None:
    missing = [name for name in REQUIRED_SOURCE_LAYERS if not layer_path(layer_dir, name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing checkpoint(s) in {layer_dir}: {', '.join(missing)}. "
            "Run scripts/main/build_hig_sources.py and scripts/main/build_widmung_v2_layers.py first."
        )


def _source_fingerprint(layer_dir: Path) -> str:
    parts = []
    for name in REQUIRED_SOURCE_LAYERS:
        parts.append(f"{name}:{layer_path(layer_dir, name).stat().st_mtime_ns}")
    return "|".join(parts)


def build_hig_family_sources(cfg: dict, grid: dict, layer_dir: Path) -> dict[str, np.ndarray]:
    """Abgeleitete HiG-Quellbänder aus den Upstream-Checkpoints.

    Reine Umbenennungen bis auf Streusiedlung UND Widmung: dort wird NÖ
    ausmaskiert, weil in NÖ ausschließlich die amtlichen SekROP-PDF-Zonen den
    750-m-Abstand definieren - sowohl für die Hüllen-Erkennung als auch für
    die Grünland-Widmungen (deren Abstand steckt in der PDF-Grünland-Klasse).
    Kein Doppelzählen, keine eigenen Abstände neben der amtlichen Quelle.
    """
    def source(name: str) -> np.ndarray:
        return read_layer_mask(layer_path(layer_dir, name))

    bl = admin_boundaries(cfg, grid["bounds"])
    noe = bl[bl["BL"].eq("Niederösterreich")] if "BL" in bl.columns else bl.iloc[0:0]
    noe_mask = raster_mask(noe[["geometry"]].copy(), 0.0, grid, "NÖ Landesfläche") if not noe.empty else np.zeros(grid["shape"], dtype=bool)

    return {
        "haeuser_im_gruenen_ferienhaus": source("ferienhaus_tourismus_source"),
        "haeuser_im_gruenen_widmung": source("official_hig_source") & ~noe_mask,
        "haeuser_im_gruenen_streusiedlung": source("hig_hulls_source") & ~noe_mask,
        "haeuser_im_gruenen_noe_pdf": source("noe_pdf_750m_zones"),
    }


def build_v2_buffers(cfg: dict, grid: dict, layer_dir: Path) -> dict[str, np.ndarray]:
    """Puffer-/Aggregatbänder des Clean-Schemas (liest die HiG-Familie mit)."""
    def source(name: str) -> np.ndarray:
        return read_layer_mask(layer_path(layer_dir, name))

    settlement = source("official_settlement_source")
    hig_family = (
        source("haeuser_im_gruenen_ferienhaus")
        | source("haeuser_im_gruenen_widmung")
        | source("haeuser_im_gruenen_streusiedlung")
    )
    noe_pdf = source("haeuser_im_gruenen_noe_pdf")

    bl = admin_boundaries(cfg, expand_bounds(grid["bounds"], max(SETTLEMENT_BUFFER_BY_BL.values()) + 25.0))

    # Die NÖ-PDF-Zonen sind bereits Objekt + 750 m und gehen deshalb UNGEPUFFERT
    # ins Aggregat - ein zweiter 750-m-Puffer würde daraus 1.500-m-Zonen machen.
    hig_aggregate = uniform_buffer_cell_mask(hig_family, HIG_FAMILY_BUFFER_M, grid, "haeuser_im_gruenen_750m") | noe_pdf

    return {
        "settlement_buffer": province_buffer_cell_mask(settlement, bl, SETTLEMENT_BUFFER_BY_BL, grid),
        "haeuser_im_gruenen": hig_aggregate,
        "nonresidential_hulls_buffer": uniform_buffer_cell_mask(source("nonresidential_hulls_source"), NONRESIDENTIAL_HULL_BUFFER_M, grid, "nonresidential_hulls_25m"),
        "cableway_buildings_buffer": uniform_buffer_cell_mask(source("cableway_buildings_source"), CABLEWAY_BUILDING_BUFFER_M, grid, "cableway_buildings_50m"),
        "general_buildings_buffer": uniform_buffer_cell_mask(source("general_buildings_source"), GENERAL_BUILDING_BUFFER_M, grid, "general_buildings_25m"),
    }


def build_wka_bestand_hulls(cfg: dict, grid: dict, layer_dir: Path, args: argparse.Namespace, valid_area: np.ndarray) -> dict[str, np.ndarray]:
    """Park-Hüllen um Bestands-Windräder außerhalb der amtlichen Windzonen.

    OSM-windpower-Punkte (Ö-weit ~1.600) werden am official_wind_zoning-Band
    getestet; die Außenseiter werden mit WKA_CLUSTER_CHAIN_M verkettet und je
    Cluster als konvexe Hülle + WKA_HULL_MARGIN_M Rand gerastert. Referenzband
    wie official_wind_zoning - beschränkt die verfügbare Fläche NICHT.
    """
    zero = np.zeros(grid["shape"], dtype=bool)
    turbines = read_layer(
        osm_layer_path(cfg, args.osm_pbf, args.osm_pbf_cache_dir, "windpower", grid["bounds"]),
        bounds=grid["bounds"],
    )
    if turbines.empty:
        print("[warn]  wka bestand: windpower layer leer", flush=True)
        return {WKA_BESTAND_BAND: zero}

    points = building_points(turbines)
    in_zone = sample_mask_at_points(read_layer_mask(layer_path(layer_dir, "official_wind_zoning")), points, grid)
    in_austria = sample_mask_at_points(valid_area, points, grid)
    outside = points[in_austria & ~in_zone]
    print(
        f"[info]  wka bestand: turbinen={len(points):,}, in Österreich={int(in_austria.sum()):,}, "
        f"in amtlicher Zone={int((in_austria & in_zone).sum()):,}, außerhalb={len(outside):,}",
        flush=True,
    )
    if not len(outside):
        return {WKA_BESTAND_BAND: zero}

    pts = gpd.GeoSeries(gpd.points_from_xy(outside[:, 0], outside[:, 1]), crs=TARGET_CRS)
    clusters = unary_union(pts.buffer(WKA_CLUSTER_CHAIN_M / 2.0).tolist())
    blobs = list(clusters.geoms) if clusters.geom_type == "MultiPolygon" else [clusters]
    hulls = []
    for blob in blobs:
        members = pts[pts.within(blob)]
        hulls.append(unary_union(members.tolist()).convex_hull.buffer(WKA_HULL_MARGIN_M))
    print(f"[info]  wka bestand: {len(hulls)} Park-Hüllen um {len(outside)} Anlagen", flush=True)
    hull_gdf = gpd.GeoDataFrame(geometry=hulls, crs=TARGET_CRS)
    return {WKA_BESTAND_BAND: raster_mask(hull_gdf, 0.0, grid, WKA_BESTAND_BAND)}


def build_settlement_variant_buffers(cfg: dict, grid: dict, layer_dir: Path, variants: dict) -> dict[str, np.ndarray]:
    """Je Variante ein Siedlungspuffer-Band um official_settlement_source."""
    if not variants:
        return {}
    source = read_layer_mask(layer_path(layer_dir, "official_settlement_source"))
    resolved = {v: resolve_variant_buffers(s) for v, s in variants.items()}
    max_dist = max((max(d.values()) for d in resolved.values()), default=0.0)
    bl = admin_boundaries(cfg, expand_bounds(grid["bounds"], max_dist + 25.0))
    out: dict[str, np.ndarray] = {}
    for vname, dists in resolved.items():
        mask = province_buffer_cell_mask(source, bl, dists, grid)
        out[f"{SETTLEMENT_VARIANT_SOURCE_BAND}_{vname}"] = mask
        print(f"[info]  settlement buffer variant {vname}: buffered_cells={int(mask.sum()):,}", flush=True)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Finales Widmungs-Abschichtungs-GeoTIFF v2 aus den Checkpoints von build_hig_sources.py + build_widmung_v2_layers.py.")
    p.add_argument("--config", default="config/config.json")
    p.add_argument("--output", default="output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif")
    p.add_argument("--layer-dir", default="output/abschichtung_widmung_v2/distance_layers")
    p.add_argument("--bbox", default=None, help="EPSG:31287 bbox minx,miny,maxx,maxy für Smoke-Tests")
    p.add_argument("--min-fragment-area-ha", type=float, default=10.0)
    p.add_argument("--official-zoning-geojson", default="data/zonierung_noe.json",
                   help="Amtliche NÖ-Windkraft-Zonierung (data.gv.at, 71 Zonen), Rohquelle. "
                        "output/webmap_export/windkraft_export_v1/vector/official_zoning.geojson "
                        "ist eine reine Attribut-Ableitung derselben 71 Features (Legacy-Webmap-"
                        "Export) und kann weiterhin per Flag übergeben werden.")
    p.add_argument("--vorrangzonen-dir", default="data/luca_zonen")
    p.add_argument("--vorrangzonen", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--settlement-variants", action=argparse.BooleanOptionalAction, default=False,
                   help="Zusätzlich 6 Siedlungsabstands-Varianten x 4 Bänder anhängen (Clean-Schema: standardmäßig aus)")
    p.add_argument("--drop-human-band", action="append", default=None, metavar="BAND",
                   help="Mensch-Band aus den Aggregaten nehmen (wiederholbar; das Band "
                        "selbst bleibt als Bedingungsband im GeoTIFF). Für Sensitivitäts-"
                        "läufe, z. B. --drop-human-band airport_runway_corridor_5km")
    p.add_argument("--osm-pbf", default="data/austria-260330.osm.pbf", help="Für den OSM-Naturschutz-Layer")
    p.add_argument("--osm-pbf-cache-dir", default="output/abschichtung/osm_pbf_layers")
    p.add_argument("--force-layers", action="store_true")
    p.add_argument("--skip-final", action="store_true", help="Nur Checkpoints, kein finales GeoTIFF")
    p.add_argument("--no-overviews", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with timed("load config/grid"):
        cfg = load_config(args.config)
        grid = load_grid(cfg, args.bbox)
    with timed("build valid area mask"):
        valid_area = build_valid_area_mask(cfg, grid)

    layer_dir = Path(args.layer_dir)
    _check_required_sources(layer_dir)
    source_fp = _source_fingerprint(layer_dir)
    variants = active_variants(args.settlement_variants)
    variant_names = [f"{SETTLEMENT_VARIANT_SOURCE_BAND}_{v}" for v in variants]

    # Sensitivitätsläufe: Bänder bleiben als Bedingung im GeoTIFF sichtbar,
    # zählen aber nicht mehr zu exclusion_human/all_exclusions/available.
    dropped = list(dict.fromkeys(args.drop_human_band or []))
    unknown = [b for b in dropped if b not in HUMAN_BANDS]
    if unknown:
        raise SystemExit(f"--drop-human-band unbekannt: {', '.join(unknown)} "
                         f"(erlaubt: {', '.join(HUMAN_BANDS)})")
    human_bands = [b for b in HUMAN_BANDS if b not in dropped]
    if dropped:
        print(f"[info]  Sensitivitätslauf ohne: {', '.join(dropped)}", flush=True)

    derived_tags = {"SOURCE_FINGERPRINT": source_fp, "BAND_SCHEMA": BAND_SCHEMA}
    # Die Abstände gehören mit in die Puffer-Tags: eine geänderte
    # SETTLEMENT_BUFFER_BY_BL/HIG_FAMILY_BUFFER_M invalidiert die
    # Puffer-Checkpoints damit von selbst.
    buffer_tags = {
        **derived_tags,
        "SETTLEMENT_BUFFER_BY_BL": json.dumps(SETTLEMENT_BUFFER_BY_BL, ensure_ascii=False, sort_keys=True),
        "HIG_FAMILY_BUFFER_M": str(HIG_FAMILY_BUFFER_M),
    }

    def _tags_ok(expected: dict):
        return lambda tags: all(tags.get(k) == v for k, v in expected.items())

    with timed("create/update checkpoint layers"):
        # Die HiG-Familie muss vor den Puffern stehen: build_v2_buffers liest
        # ihre Checkpoints für das 750-m-Aggregat.
        ensure_group_layers(
            layer_dir, HIG_FAMILY_SOURCE_BANDS, "HiG family sources",
            lambda: build_hig_family_sources(cfg, grid, layer_dir), grid, args.force_layers,
            extra_ok=_tags_ok(derived_tags), extra_tags=derived_tags,
        )
        ensure_group_layers(
            layer_dir, BUFFER_BANDS, "v2 buffers",
            lambda: build_v2_buffers(cfg, grid, layer_dir), grid, args.force_layers,
            extra_ok=_tags_ok(buffer_tags), extra_tags=buffer_tags,
        )
        if variant_names:
            ensure_group_layers(
                layer_dir, variant_names, "settlement buffer variants",
                lambda: build_settlement_variant_buffers(cfg, grid, layer_dir, variants), grid, args.force_layers,
                extra_ok=_tags_ok(buffer_tags), extra_tags=buffer_tags,
            )
        ensure_group_layers(layer_dir, NATURE_BANDS, "nature masks", lambda: build_nature_masks(cfg, grid, args), grid, args.force_layers)
        ensure_group_layers(layer_dir, GEOGRAPHY_BANDS, "geography masks", lambda: build_geography_masks(cfg, grid), grid, args.force_layers)
        ensure_group_layers(layer_dir, WATER_BANDS, "water masks", lambda: build_water_masks(cfg, grid, args), grid, args.force_layers)
        # Kein extra_ok/extra_tags hier: layer_done() prueft nur shape/crs/transform/
        # Bandname, keinen Fingerprint der Eingabedatei (siehe layer_done() in
        # abschichtung_common.py). Ein vorhandener official_wind_zoning.tif-
        # Checkpoint aus einem Lauf VOR dieser Umstellung (alter Default
        # output/webmap_export/.../official_zoning.geojson) wird also still
        # weiterverwendet, auch wenn jetzt data/zonierung_noe.json als Default
        # gilt - der neue Pfad wirkt erst nach --force-layers. In diesem Fall
        # unkritisch, da beide Dateien geometrisch identisch sind (71 Features,
        # Sep 2026 geprueft), aber bei kuenftigen Aenderungen an der Rohquelle
        # relevant.
        ensure_group_layers(layer_dir, OFFICIAL_ZONING_BANDS, "official wind zoning reference", lambda: build_official_zoning_masks(cfg, grid, args), grid, args.force_layers)
        # Nach dem Zoning-Band: der WKA-Bestand testet seine Punkte daran.
        wka_tags = {
            "BAND_SCHEMA": BAND_SCHEMA,
            "WKA_PARAMS": f"chain={WKA_CLUSTER_CHAIN_M:g}|margin={WKA_HULL_MARGIN_M:g}|zoning={layer_path(layer_dir, OFFICIAL_ZONING_BANDS[0]).stat().st_mtime_ns}",
        }
        ensure_group_layers(
            layer_dir, [WKA_BESTAND_BAND], "wka bestand hulls",
            lambda: build_wka_bestand_hulls(cfg, grid, layer_dir, args, valid_area), grid, args.force_layers,
            extra_ok=lambda tags: all(tags.get(k) == v for k, v in wka_tags.items()), extra_tags=wka_tags,
        )

    if args.skip_final:
        print(f"Checkpoint layers updated in {layer_dir}; skipped final composition.")
        return

    tags = {
        "MIN_FRAGMENT_AREA_HA": str(args.min_fragment_area_ha),
        "PIPELINE": PIPELINE_TAG,
        "BAND_SCHEMA": BAND_SCHEMA,
        "SETTLEMENT_BUFFER_BY_BL": json.dumps(SETTLEMENT_BUFFER_BY_BL, ensure_ascii=False, sort_keys=True),
        "HIG_FAMILY_BUFFER_M": str(HIG_FAMILY_BUFFER_M),
        "NONRESIDENTIAL_HULL_BUFFER_M": str(NONRESIDENTIAL_HULL_BUFFER_M),
        "HIG_CHAIN_M": str(HIG_CHAIN_M),
        "HIG_MIN_ADRESSEN": str(HIG_MIN_ADRESSEN),
        "DROPPED_HUMAN_BANDS": ",".join(dropped) if dropped else "keine",
        "CABLEWAY_BUILDING_BUFFER_M": str(CABLEWAY_BUILDING_BUFFER_M),
        "GENERAL_BUILDING_BUFFER_M": str(GENERAL_BUILDING_BUFFER_M),
        "HIG_SOURCE": "amtliche Widmung + NÖ-SekROP-PDF + DKM-Hüllen + BEV-Adressregister (build_hig_sources.py); NÖ-Streusiedlung durch PDF ersetzt",
        "WICHTIGE_OBJEKTE": "in haeuser_im_gruenen (750 m); vorher eigenes 250-m-Band",
        "BEWOHNTE_EINZELLAGEN": "in general_buildings_source (25 m); vorher eigenes 25-m-Bandpaar",
        "POWER_LINES": "kein Ausschlusskriterium (Clean-Schema Aug 2026)",
        "AIRPORT_CORRIDOR_LENGTH_M": str(AIRPORT_CORRIDOR_LENGTH_M),
        "AIRPORT_CORRIDOR_HALF_ANGLE_DEG": str(AIRPORT_CORRIDOR_HALF_ANGLE_DEG),
        "WIEN": "amtliche Widmung Stadt Wien (GENFLWIDMUNGOGD), kein Vollausschluss mehr",
        "WATER_MIN_AREA_HA": str(WATER_MIN_AREA_HA),
        "UNCERTAINTY_BLUR_SIGMAS_M": ",".join(f"{s:g}" for s in UNCERTAINTY_BLUR_SIGMAS_M),
        "SETTLEMENT_BUFFER_VARIANTS": json.dumps({v: resolve_variant_buffers(s) for v, s in variants.items()}, sort_keys=True, ensure_ascii=False),
        "SETTLEMENT_BUFFER_VARIANT_NAMES": ",".join(variants.keys()),
        "UNCERTAINTY_BLUR_SOURCE": "available_after_all_exclusions_raw",
        "WKA_CLUSTER_CHAIN_M": str(WKA_CLUSTER_CHAIN_M),
        "WKA_HULL_MARGIN_M": str(WKA_HULL_MARGIN_M),
        "DISTANCE_ENGINE": "fft",
    }

    with timed(f"compose final GeoTIFF {args.output}"):
        band_names = compose_exclusion_geotiff(
            path=Path(args.output),
            grid=grid,
            layer_dir=layer_dir,
            condition_bands=[b.name for b in BANDS],
            human_bands=human_bands,
            nature_band_names=NATURE_BANDS,
            geography_band_names=[*GEOGRAPHY_BANDS, *WATER_BANDS],
            valid_area=valid_area,
            min_fragment_area_ha=args.min_fragment_area_ha,
            trailing_bands=[*OFFICIAL_ZONING_BANDS, WKA_BESTAND_BAND],
            variant_source_band=SETTLEMENT_VARIANT_SOURCE_BAND,
            variants=variants,
            tags=tags,
            build_overviews=not args.no_overviews,
            blur_sigmas_m=UNCERTAINTY_BLUR_SIGMAS_M,
            blur_source="raw",
        )

    print(
        f"Wrote {args.output} from checkpoint layers in {layer_dir} "
        f"({len(BANDS)} condition bands + 3 category aggregates + all/raw/cleaned + "
        f"{len(UNCERTAINTY_BLUR_SIGMAS_M)} uncertainty blur bands + "
        f"official_zoning + wka_bestand + {len(variants)} settlement-buffer variants x 4 bands "
        f"= {len(band_names)} bands), shape={grid['shape']}"
    )


if __name__ == "__main__":
    main()
