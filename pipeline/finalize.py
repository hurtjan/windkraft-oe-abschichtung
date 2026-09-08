"""Finalisierung: das 38-Band-GeoTIFF plus Manifest (Paket W3.1,
docs/rewrite/PLAN.md §7, §13.9).

Reiner Komponist. Diese Stufe baut KEINEN einzigen Layer selbst - alle 33
Checkpoints unter ``build/layers/`` sind bereits von der Layer-Welle
geschrieben (W2.1 ``pipeline/layers/hig.py``, W2.3 ``pipeline/layers/osm.py``,
W2.4 ``pipeline/layers/geo.py`` - siehe ``make layers``). Was hier passiert,
ist genau der Teil von ``scripts/widmung_v2/04_create_distance_zones.py``
(seit W6.1 aus dem Repo entfernt; letzter Stand im Commit ``f1d00f7``,
abrufbar mit ``git show f1d00f7:scripts/widmung_v2/04_create_distance_zones.py``),
der NACH dessen sieben ``ensure_group_layers()``-Aufrufen kommt: die 26
Bedingungsbänder plus die beiden Referenzbänder einlesen, die Kategorie- und
Ergebnisaggregate bilden, die vier Unschärfebänder rechnen und alles
zusammen mit dem Manifest schreiben (``compose_exclusion_geotiff()`` +
``write_band_manifest()``, beide unverändert aus
``windkraft/calc/abschichtung_common.py`` bzw.
``windkraft/calc/band_manifest.py`` importiert - reine Rechenlogik, hier
nicht neu erfunden).

## Wo die Grenze zu Welle 2 verläuft

``pipeline/layers/geo.py`` endet, sobald der letzte der 17 dort gebauten
Checkpoints steht (siehe dessen Moduldocstring: "Diese Datei endet, sobald
die letzte der 17 Rastermasken als Checkpoint geschrieben ist"). Diese Datei
beginnt genau dort - sie ruft KEIN ``ensure_group_layers()`` auf, sondern
verlangt alle 33 Checkpoints als harte Vorbedingung (``_check_layers()``
unten) und bricht ab, wenn einer fehlt, statt ihn selbst zu bauen. Das ist
Regel aus PLAN.md §3: "Jede Stufe darf nur aus der vorigen lesen."

## Regel 4: Werte unverändert übernommen, nicht verbessert

``BANDS`` (die 26 Bedingungsbänder samt Beschreibung), ``HUMAN_BANDS``, die
Tag-Konstruktion und alle Puffer-/Schwellenwert-Konstanten sind wortgleich
aus ``scripts/widmung_v2/04_create_distance_zones.py`` übernommen (seit W6.1
aus dem Repo entfernt; letzter Stand im Commit ``f1d00f7``, abrufbar mit
``git show f1d00f7:scripts/widmung_v2/04_create_distance_zones.py``) - exakt
dasselbe Vorgehen wie in ``pipeline/layers/geo.py`` (dessen Moduldocstring:
"Regel 4: Werte/Namen unverändert") und aus demselben Grund: das alte
Skript war kein Paket (numerischer Dateiname, kein gültiger Modulpfad für
einen normalen ``import``). Die Altkette selbst (``make widmung-v2``) ist
seit W6.1 entfernt (docs/rewrite/FORTSCHRITT.md) - dieser Abschnitt
beschreibt weiterhin die Herkunft der Werte, nicht mehr eine parallel
lauffähige Kette.

## Bewusst NICHT übernommen (mit Begründung, wie schon bei W2.4)

- **Siedlungsabstands-Varianten** (``--settlement-variants``,
  ``SETTLEMENT_BUFFER_VARIANTS``, ``build_settlement_variant_buffers``):
  ``pipeline/layers/geo.py`` baut deren Quell-Checkpoints
  (``settlement_buffer_<variante>``) gar nicht erst - sie stehen nicht in
  ``pipeline.contract.LAYER_NAMES`` (33 Einträge) und sind im Clean-Schema
  per Default aus. Ohne Quell-Checkpoint keine Variantenbänder hier.
- **``--drop-human-band`` (Sensitivitätsläufe):** eine Lauf-Option des alten
  Skripts für Sonderauswertungen außerhalb der Standardkette, kein Teil der
  38-Band-Abschichtung selbst.
- **``--official-zoning-geojson``/``--vorrangzonen-dir``/``--osm-pbf``:** die
  amtlichen Windzonen und der WKA-Bestand sind bereits fertige Checkpoints
  aus W2.4 (``official_wind_zoning``, ``wka_bestand_ausserhalb_zonen``) -
  diese Stufe liest sie nur noch, baut sie nicht mehr aus Rohdaten.

## valid_area: kein Checkpoint, aber auch keine Rohdatei

``valid_area`` (die Staatsgebietsmaske, mit der ``compose_exclusion_geotiff()``
die Aggregat-/Ergebnisbänder verschneidet) steht nicht in
``pipeline.contract.LAYER_NAMES`` - sie war auch im alten Schema kein
persistierter Bandtyp, sondern wurde in ``main()`` jedes Mal frisch aus den
Verwaltungsgrenzen gebaut. Diese Datei importiert dafür
``pipeline.layers.geo._build_valid_area_mask()`` (liest
``build/prep/admin/bundesland_masken.gpkg``, siehe dessen Modul) statt sie
ein drittes Mal zu duplizieren oder auf die VGD-Rohquelle
(``abschichtung_common.build_valid_area_mask()``) zurückzugreifen - Letzteres
wäre ein Sprung von Stufe 5 direkt auf Stufe 1 und würde §3 verletzen ("nie
zwei Stufen überspringen").

## §13.9 / Regel 8: die erste erklärte Abweichung

``geography_water_bodies`` weicht bekanntermaßen in 543.106 von 336.038.001
Zellen ab, ausschließlich zusätzlich (PLAN.md §13.9) - die neue Prep-Stufe
filtert gegen die ungeklippte OSM-Rohquelle und findet eine
grenzüberschreitende Bodensee-Relation, die der alte ``osmium extract
--bbox``-Weg verliert. Diese Datei ändert daran nichts (Regel 8: "wird
weitergetragen, nicht weggemacht") - sie liest den Checkpoint, den
``pipeline/layers/geo.py`` geschrieben hat, unverändert. Die Ausbreitung
dieser einen Abweichung auf die übrigen 37 Bänder ist Gegenstand des
Berichts zu diesem Paket, nicht dieser Datei.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract, runtime  # noqa: E402
from pipeline.layers.geo import _build_valid_area_mask  # noqa: E402

from windkraft.config import load_config  # noqa: E402
from windkraft.calc.abschichtung_common import (  # noqa: E402
    AIRPORT_CORRIDOR_HALF_ANGLE_DEG,
    AIRPORT_CORRIDOR_LENGTH_M,
    CABLEWAY_BUILDING_BUFFER_M,
    GENERAL_BUILDING_BUFFER_M,
    GEOGRAPHY_BANDS,
    HIG_CHAIN_M,
    HIG_FAMILY_BUFFER_M,
    HIG_MIN_ADRESSEN,
    NATURE_BANDS,
    NONRESIDENTIAL_HULL_BUFFER_M,
    OFFICIAL_ZONING_BANDS,
    SETTLEMENT_BUFFER_BY_BL,
    UNCERTAINTY_BLUR_SIGMAS_M,
    WATER_BANDS,
    WATER_MIN_AREA_HA,
    compose_exclusion_geotiff,
    layer_path,
    load_grid,
    timed,
)
from windkraft.calc.band_manifest import write_band_manifest  # noqa: E402

PIPELINE_TAG = "widmung_v2"
# Wortgleich aus scripts/widmung_v2/04_create_distance_zones.py (dort Zeile
# ~130; seit W6.1 aus dem Repo entfernt, letzter Stand im Commit f1d00f7 -
# git show f1d00f7:scripts/widmung_v2/04_create_distance_zones.py) und
# pipeline/layers/geo.py (dort Zeile ~176) übernommen - derselbe Tag-Wert
# muss über alle drei Stellen hinweg gleich bleiben, sonst würde
# layer_done() (Fingerabdruck-Vergleich) Checkpoints fälschlich als veraltet
# ansehen.
BAND_SCHEMA = "clean-38-ohne-wichtige-objekte-aug-2026"

WKA_BESTAND_BAND = "wka_bestand_ausserhalb_zonen"
WKA_CLUSTER_CHAIN_M = 750.0
WKA_HULL_MARGIN_M = 200.0


@dataclass(frozen=True)
class Band:
    name: str
    description: str


# Wortgleich aus scripts/widmung_v2/04_create_distance_zones.py:BANDS (dort
# Zeile ~147-174; seit W6.1 aus dem Repo entfernt, letzter Stand im Commit
# f1d00f7 - git show f1d00f7:scripts/widmung_v2/04_create_distance_zones.py)
# übernommen - die 26 Bedingungsbänder in exakt der Reihenfolge, in der
# compose_exclusion_geotiff() sie schreibt.
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

# Wortgleich aus scripts/widmung_v2/04_create_distance_zones.py:HUMAN_BANDS
# (seit W6.1 aus dem Repo entfernt, letzter Stand im Commit f1d00f7 - git
# show f1d00f7:scripts/widmung_v2/04_create_distance_zones.py).
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

# Alle 33 Checkpoints, die diese Stufe als harte Vorbedingung verlangt -
# identisch mit pipeline.contract.LAYER_NAMES (dort vorab erklärt); hier noch
# einmal als flache Liste, weil _check_layers() nur Namen braucht, keine
# Pfade (die liefert layer_path() je nach --layer-dir).
REQUIRED_LAYERS = list(contract.LAYER_NAMES)


def _check_layers(layer_dir: Path) -> None:
    """Harte Vorbedingung statt stillem Fallback (PLAN.md §3, Stufe 5).

    Anders als das alte Skript (das acht fehlende Checkpoints selbst baut,
    siehe _check_required_sources() in 04_create_distance_zones.py - seit
    W6.1 aus dem Repo entfernt, letzter Stand im Commit f1d00f7: git show
    f1d00f7:scripts/widmung_v2/04_create_distance_zones.py) prüft diese
    Stufe ALLE 33 Checkpoints und baut keinen einzigen davon - Bauen ist
    Aufgabe der Layer-Welle (W2.1/W2.3/W2.4), nicht dieser Stufe.
    """
    missing = [name for name in REQUIRED_LAYERS if not layer_path(layer_dir, name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Fehlende Checkpoint-Layer in {layer_dir}: {', '.join(missing)}. "
            "Diese Stufe baut keine Layer selbst - 'make layers' zuerst laufen lassen "
            "(pipeline/layers/hig.py, osm.py, geo.py)."
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Finalisierung W3.1: komponiert das 38-Band-GeoTIFF plus Manifest "
            "aus den Checkpoint-Layern der neuen Kette (build/layers/, siehe "
            "'make layers'). Baut selbst keine Layer."
        )
    )
    p.add_argument("--config", default="config.json")
    p.add_argument(
        "--layer-dir",
        default=None,
        help="Quelle der 33 Checkpoint-Layer. Default: pipeline.contract.BUILD_LAYERS (build/layers/).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Ziel-GeoTIFF. Default: pipeline.contract.PRODUCTS['abschichtung_tif'] (out/abschichtung.tif).",
    )
    # Kein --bbox (anders als beim alten Skript und bei pipeline/layers/*.py):
    # die 33 Checkpoints unter --layer-dir sind bereits auf dem vollen
    # Österreich-Gitter geschrieben (build/layers/, siehe make layers). Ein
    # hier verkleinertes Gitter würde beim ersten read_layer_mask() sofort an
    # der Shape scheitern (getestet: (2000,2000) vs. (14001,24001)) - ein
    # bbox-Smoke-Test müsste auch die Checkpoints selbst neu (verkleinert)
    # bauen, und genau das ist nicht Aufgabe dieser Stufe (siehe
    # _check_layers()). Wer diese Stufe klein testen will, braucht ein
    # eigenes --layer-dir mit bbox-verkleinerten Checkpoints.
    p.add_argument("--min-fragment-area-ha", type=float, default=10.0)
    p.add_argument("--no-overviews", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    layer_dir = Path(args.layer_dir) if args.layer_dir else contract.BUILD_LAYERS
    output = Path(args.output) if args.output else contract.PRODUCTS["abschichtung_tif"]

    with timed("load config/grid"):
        cfg = load_config(args.config)
        grid = load_grid(cfg, None)

    _check_layers(layer_dir)

    with timed("build valid area mask (build/prep/admin)"):
        valid_area = _build_valid_area_mask(grid)

    # Wortgleich aus scripts/widmung_v2/04_create_distance_zones.py:main()
    # (dort Zeile ~472-499; seit W6.1 aus dem Repo entfernt, letzter Stand im
    # Commit f1d00f7 - git show f1d00f7:scripts/widmung_v2/04_create_distance_zones.py)
    # übernommen, abzüglich der Varianten-/Drop-Tags (siehe Moduldocstring:
    # bewusst nicht übernommen -> DROPPED_HUMAN_BANDS bleibt "keine",
    # SETTLEMENT_BUFFER_VARIANTS bleibt "{}").
    tags = {
        "MIN_FRAGMENT_AREA_HA": str(args.min_fragment_area_ha),
        "PIPELINE": PIPELINE_TAG,
        "BAND_SCHEMA": BAND_SCHEMA,
        "SETTLEMENT_BUFFER_BY_BL": json.dumps(SETTLEMENT_BUFFER_BY_BL, ensure_ascii=False, sort_keys=True),
        "HIG_FAMILY_BUFFER_M": str(HIG_FAMILY_BUFFER_M),
        "NONRESIDENTIAL_HULL_BUFFER_M": str(NONRESIDENTIAL_HULL_BUFFER_M),
        "HIG_CHAIN_M": str(HIG_CHAIN_M),
        "HIG_MIN_ADRESSEN": str(HIG_MIN_ADRESSEN),
        "DROPPED_HUMAN_BANDS": "keine",
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
        "SETTLEMENT_BUFFER_VARIANTS": "{}",
        "SETTLEMENT_BUFFER_VARIANT_NAMES": "",
        "UNCERTAINTY_BLUR_SOURCE": "available_after_all_exclusions_raw",
        "WKA_CLUSTER_CHAIN_M": str(WKA_CLUSTER_CHAIN_M),
        "WKA_HULL_MARGIN_M": str(WKA_HULL_MARGIN_M),
        "DISTANCE_ENGINE": "fft",
    }

    with timed(f"compose final GeoTIFF {output}"):
        runtime.ensure_dir(output.parent)
        band_names = compose_exclusion_geotiff(
            path=output,
            grid=grid,
            layer_dir=layer_dir,
            condition_bands=[b.name for b in BANDS],
            human_bands=HUMAN_BANDS,
            nature_band_names=NATURE_BANDS,
            geography_band_names=[*GEOGRAPHY_BANDS, *WATER_BANDS],
            valid_area=valid_area,
            min_fragment_area_ha=args.min_fragment_area_ha,
            trailing_bands=[*OFFICIAL_ZONING_BANDS, WKA_BESTAND_BAND],
            variant_source_band=None,
            variants={},
            tags=tags,
            build_overviews=not args.no_overviews,
            blur_sigmas_m=UNCERTAINTY_BLUR_SIGMAS_M,
            blur_source="raw",
        )

    # Sidecar direkt aus dem, was gerade geschrieben wurde - wie im alten
    # Skript: band_names ist die tatsächliche Bandreihenfolge, tags sind die
    # Datei-Tags. Kein zweites Öffnen des Rasters, keine zweite Wahrheit.
    manifest_path = write_band_manifest(
        output, band_names, tags, grid, {b.name: b.description for b in BANDS}
    )

    print(
        f"Wrote {output} from checkpoint layers in {layer_dir} "
        f"({len(BANDS)} condition bands + 3 category aggregates + all/raw/cleaned + "
        f"{len(UNCERTAINTY_BLUR_SIGMAS_M)} uncertainty blur bands + "
        f"official_zoning + wka_bestand = {len(band_names)} bands), shape={grid['shape']}"
    )
    print(f"Wrote {manifest_path} ({len(band_names)} bands, schema {tags['BAND_SCHEMA']})")


if __name__ == "__main__":
    main()
