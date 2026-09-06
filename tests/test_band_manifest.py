"""Unit-Tests für den Band-Manifest-Writer.

Synthetische Eingaben - kein echtes Raster. Geprüft wird der Vertrag, auf den
sich der Dashboard-Konsument verlässt: 38 Bänder, Namen/Reihenfolge exakt wie
übergeben, zehn Pflichtfelder je Band, value_type nur bei den vier
Unschärfebändern "percent_0_100", clipped_to_austria nur bei 27-36, jede
Kategorie in category_order, Farben als 4 Ints in [0, 255], parameters
unverändert, NÖ-DKM-Caveat vorhanden.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from affine import Affine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.band_manifest import (  # noqa: E402
    build_band_manifest,
    manifest_path_for,
    write_band_manifest,
)

# Die 26 Bedingungsbänder des Clean-38-Schemas, in genau der Reihenfolge, in
# der scripts/widmung_v2/04_create_distance_zones.py sie schreibt.
CONDITION_BANDS = [
    "official_settlement_source",
    "settlement_buffer",
    "haeuser_im_gruenen_ferienhaus",
    "haeuser_im_gruenen_widmung",
    "haeuser_im_gruenen_streusiedlung",
    "haeuser_im_gruenen_noe_pdf",
    "haeuser_im_gruenen",
    "nonresidential_hulls_source",
    "nonresidential_hulls_buffer",
    "cableway_buildings_source",
    "cableway_buildings_buffer",
    "general_buildings_source",
    "general_buildings_buffer",
    "road_motorway_trunk",
    "road_federal_state",
    "rail_main",
    "cableway_people_150m",
    "military_restricted_area",
    "airport_area_major",
    "airport_runway_corridor_5km",
    "nature_protection_areas",
    "osm_nature_protection_areas",
    "geography_slope_too_steep",
    "geography_elevation_too_high",
    "geography_wind_too_low",
    "geography_water_bodies",
]

BAND_NAMES = [
    *CONDITION_BANDS,
    "exclusion_human",
    "exclusion_nature",
    "exclusion_geography",
    "all_exclusions",
    "available_after_all_exclusions_raw",
    "available_cleaned_min_10ha",
    "available_blur_sigma_100m",
    "available_blur_sigma_200m",
    "available_blur_sigma_250m",
    "available_blur_sigma_300m",
    "official_wind_zoning",
    "wka_bestand_ausserhalb_zonen",
]

# Das echte Tag-Dict, verkürzt auf Platzhalterwerte, aber mit den tatsächlichen
# Schlüsseln und ausschließlich String-Werten.
#
# ACHTUNG: es sind 26 Schlüssel, nicht 27. Nachgezählt am `tags`-Dict in
# scripts/widmung_v2/04_create_distance_zones.py (und identisch im Alt-Repo,
# scripts/main/create_widmung_v2_distance_zones.py). Das fertige Referenz-TIF
# trägt sogar nur 25 davon plus GDALs AREA_OR_POINT: es wurde gebaut, bevor
# SETTLEMENT_BUFFER_VARIANT_NAMES hinzukam. Der Writer reicht durch, was er
# bekommt, und zählt nichts nach.
TAGS = {
    "MIN_FRAGMENT_AREA_HA": "10.0",
    "PIPELINE": "widmung_v2",
    "BAND_SCHEMA": "clean-38-ohne-wichtige-objekte-aug-2026",
    "SETTLEMENT_BUFFER_BY_BL": '{"Niederösterreich": 1200.0}',
    "HIG_FAMILY_BUFFER_M": "750.0",
    "NONRESIDENTIAL_HULL_BUFFER_M": "25.0",
    "HIG_CHAIN_M": "200.0",
    "HIG_MIN_ADRESSEN": "5",
    "DROPPED_HUMAN_BANDS": "keine",
    "CABLEWAY_BUILDING_BUFFER_M": "50.0",
    "GENERAL_BUILDING_BUFFER_M": "25.0",
    "HIG_SOURCE": "amtliche Widmung + NÖ-SekROP-PDF + DKM-Hüllen + BEV-Adressregister",
    "WICHTIGE_OBJEKTE": "in haeuser_im_gruenen (750 m)",
    "BEWOHNTE_EINZELLAGEN": "in general_buildings_source (25 m)",
    "POWER_LINES": "kein Ausschlusskriterium (Clean-Schema Aug 2026)",
    "AIRPORT_CORRIDOR_LENGTH_M": "5000.0",
    "AIRPORT_CORRIDOR_HALF_ANGLE_DEG": "15.0",
    "WIEN": "amtliche Widmung Stadt Wien (GENFLWIDMUNGOGD)",
    "WATER_MIN_AREA_HA": "1.0",
    "UNCERTAINTY_BLUR_SIGMAS_M": "100,200,250,300",
    "SETTLEMENT_BUFFER_VARIANTS": "{}",
    "SETTLEMENT_BUFFER_VARIANT_NAMES": "",
    "UNCERTAINTY_BLUR_SOURCE": "available_after_all_exclusions_raw",
    "WKA_CLUSTER_CHAIN_M": "750.0",
    "WKA_HULL_MARGIN_M": "200.0",
    "DISTANCE_ENGINE": "fft",
}

GRID = {
    "shape": (14001, 24001),
    "transform": Affine(25.0, 0.0, 107000.0, 0.0, -25.0, 576025.0),
    "crs": "EPSG:31287",
    "bounds": (107000.0, 226000.0, 707025.0, 576025.0),
}

CONDITION_DESCRIPTIONS = {name: f"Beschreibung für {name}" for name in CONDITION_BANDS}

REQUIRED_BAND_FIELDS = [
    "index",
    "name",
    "label_de",
    "description_de",
    "category",
    "value_type",
    "clipped_to_austria",
    "is_total",
    "color_rgba",
    "default_visible",
]

PERCENT_INDICES = {33, 34, 35, 36}
CLIPPED_INDICES = set(range(27, 37))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_band_manifest(
        Path("/nowhere/osm_wka_distance_zones_widmung_v2.tif"),
        BAND_NAMES,
        TAGS,
        GRID,
        CONDITION_DESCRIPTIONS,
    )


def test_tags_fixture_matches_the_real_tag_dict():
    # Gegen das echte tags-Dict gezählt: 26 Schlüssel.
    assert len(TAGS) == 26
    assert all(isinstance(v, str) for v in TAGS.values())


def test_band_count_is_38(manifest):
    assert manifest["band_count"] == 38
    assert len(manifest["bands"]) == 38


def test_band_names_and_order_match_input(manifest):
    assert [b["name"] for b in manifest["bands"]] == BAND_NAMES
    assert [b["index"] for b in manifest["bands"]] == list(range(1, 39))


def test_every_band_has_all_required_fields(manifest):
    for band in manifest["bands"]:
        missing = [field for field in REQUIRED_BAND_FIELDS if field not in band]
        assert not missing, f"{band['name']}: fehlende Felder {missing}"


def test_value_type_percent_only_for_bands_33_to_36(manifest):
    for band in manifest["bands"]:
        expected = "percent_0_100" if band["index"] in PERCENT_INDICES else "binary"
        assert band["value_type"] == expected, band["name"]


def test_clipped_to_austria_only_for_bands_27_to_36(manifest):
    for band in manifest["bands"]:
        assert band["clipped_to_austria"] is (band["index"] in CLIPPED_INDICES), band["name"]


def test_every_category_appears_in_category_order(manifest):
    order = manifest["category_order"]
    for band in manifest["bands"]:
        assert band["category"] in order, band["name"]


def test_color_rgba_is_four_ints_in_range(manifest):
    for band in manifest["bands"]:
        color = band["color_rgba"]
        assert isinstance(color, list) and len(color) == 4, band["name"]
        for component in color:
            assert isinstance(component, int) and 0 <= component <= 255, band["name"]


def test_parameters_pass_through_tags_unchanged(manifest):
    # Kein Längen-Check hier: `parameters` ist Dokumentation, kein Schema. Das
    # echte Referenz-TIF traegt nur 25 Tags (vor SETTLEMENT_BUFFER_VARIANT_NAMES
    # gebaut), waehrend TAGS hier 26 hat - der Writer prueft die Anzahl nicht
    # nach, und dieser Test soll das nicht implizit tun.
    assert manifest["parameters"] == TAGS


def test_raster_block_matches_grid(manifest):
    raster = manifest["raster"]
    assert raster["crs"] == "EPSG:31287"
    assert raster["width"] == 24001
    assert raster["height"] == 14001
    assert raster["pixel_size_m"] == 25.0
    assert raster["bounds"] == list(GRID["bounds"])
    assert raster["dtype"] == "uint8"
    assert raster["nodata"] == 0
    assert "kein echtes NoData" in raster["nodata_meaning"]


def test_top_level_shape(manifest):
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["pipeline"] == "widmung_v2"
    assert manifest["band_schema"] == "clean-38-ohne-wichtige-objekte-aug-2026"
    assert manifest["raster_file"] == "osm_wka_distance_zones_widmung_v2.tif"
    assert manifest["generated_at"].endswith("Z")


def test_descriptions_wired_through_for_condition_bands(manifest):
    for band in manifest["bands"][:26]:
        assert band["description_de"] == f"Beschreibung für {band['name']}"
    for band in manifest["bands"][26:]:
        assert band["description_de"], band["name"]


def test_noe_dkm_caveat_present_with_numbers(manifest):
    caveats = manifest["caveats"]
    match = [c for c in caveats if c["id"] == "noe_dkm_reconstructed"]
    assert len(match) == 1
    caveat = match[0]
    assert caveat["numbers"] == {
        "polygons_total": 3491407,
        "ambiguous": 684249,
        "unassigned": 338674,
    }
    assert caveat["severity"] == "methodisch"
    assert caveat["applies_to_other_states"] is False
    assert caveat["affects"]["bundesland"] == "NÖ"
    assert caveat["affects"]["bands"] == [8, 9, 12, 13, 27, 30, 31, 32, 33, 34, 35, 36]
    # Wirkungspfad bis Band 32 (die veröffentlichte Potenzialfläche) muss im
    # Fließtext benannt sein, nicht nur implizit über die Bandliste.
    assert "Band 32" in caveat["text_de"]
    assert "33-36" in caveat["text_de"]


def test_blur_bleed_caveat_present_for_bands_33_to_36(manifest):
    caveats = manifest["caveats"]
    match = [c for c in caveats if c["id"] == "blur_bands_bleed_across_border"]
    assert len(match) == 1
    caveat = match[0]
    assert caveat["severity"] == "methodisch"
    assert caveat["affects"]["bands"] == [33, 34, 35, 36]


def test_exactly_two_caveats_present(manifest):
    ids = {c["id"] for c in manifest["caveats"]}
    assert ids == {"noe_dkm_reconstructed", "blur_bands_bleed_across_border"}


def test_pixel_size_accepts_plain_affine_tuple():
    # Fallback-Pfad ohne affine.Affine (a, b, c, d, e, f).
    grid = dict(GRID, transform=(25.0, 0.0, 107000.0, 0.0, -25.0, 576025.0))
    built = build_band_manifest(Path("/nowhere/x.tif"), BAND_NAMES, TAGS, grid, CONDITION_DESCRIPTIONS)
    assert built["raster"]["pixel_size_m"] == 25.0


def test_manifest_path_is_derived_from_raster_stem(tmp_path):
    tif = tmp_path / "sub" / "osm_wka_distance_zones_widmung_v2.tif"
    assert manifest_path_for(tif).name == "osm_wka_distance_zones_widmung_v2.bands.json"
    assert manifest_path_for(tif).parent == tif.parent


def test_written_file_round_trips_through_json(tmp_path):
    tif = tmp_path / "osm_wka_distance_zones_widmung_v2.tif"
    out = write_band_manifest(tif, BAND_NAMES, TAGS, GRID, CONDITION_DESCRIPTIONS)
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["band_count"] == 38
    assert [b["name"] for b in loaded["bands"]] == BAND_NAMES
    assert loaded["parameters"] == TAGS
