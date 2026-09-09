"""Unit-Tests für den Band-Manifest-Writer.

Synthetische Eingaben - kein echtes Raster. Geprüft wird der Vertrag, auf den
sich der Dashboard-Konsument verlässt: 44 Bänder (Schema 2.2.0, Paket W7.1),
Namen/Reihenfolge exakt wie übergeben, Pflichtfelder je Band (inkl. familie/
stufe/dashboard_layer seit 2.2.0), value_type nur bei den vier
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

from calc.band_manifest import (  # noqa: E402
    build_band_manifest,
    manifest_path_for,
    write_band_manifest,
)

# Die 26 Bedingungsbänder des Clean-Schemas (seit Schema 2.2.0/W7.1
# "clean-44-..."), in genau der Reihenfolge, in der
# scripts/widmung_v2/04_create_distance_zones.py sie schreibt.
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
    # Bänder 39-44, Schema 2.2.0 (W7.1) - schnittstelle-manifest-2.2.md §2.
    "haeuser_im_gruenen_source",
    "general_buildings_roh_osm",
    "general_buildings_roh_dkm",
    "sources_human",
    "sources_nature",
    "sources_geography",
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
    "BAND_SCHEMA": "clean-44-ohne-wichtige-objekte-aug-2026",
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
    # Ab Schema 2.0.0 (Paket W3.1, docs/rewrite/PLAN.md §7): Nummer/Name/
    # Rolle/Puffer/Quelle je Band, siehe Moduldocstring von band_manifest.py.
    "rolle",
    "puffer_m",
    "puffer_hinweis",
    "quelle",
    "abgeleitet_von",
    # Ab Schema 2.2.0 (Paket W7.1, docs/rewrite/PLAN.md, schnittstelle-
    # manifest-2.2.md §1): familie/stufe/dashboard_layer.
    "familie",
    "stufe",
    "dashboard_layer",
]

PERCENT_INDICES = {33, 34, 35, 36}
CLIPPED_INDICES = set(range(27, 37))

# Rolle je Bandbereich (Schema 2.0.0, erweitert um 39-44 in 2.2.0/W7.1) -
# deckungsgleich mit der Ampel-Logik von PLAN.md §6 (1-26 Bedingung, 27-29
# Kategorie-Aggregate, 30 Gesamt-Aggregat, 31 roh, 32 bereinigt, 33-36
# Unschärfe, 37-38 Referenz, 39-41 Bedingung, 42-44 Kategorie-Aggregate).
EXPECTED_ROLE_BY_INDEX = {
    **{i: "bedingung" for i in range(1, 27)},
    27: "aggregat_kategorie",
    28: "aggregat_kategorie",
    29: "aggregat_kategorie",
    30: "aggregat_gesamt",
    31: "verfuegbarkeit_roh",
    32: "verfuegbarkeit_bereinigt",
    33: "unschaerfe",
    34: "unschaerfe",
    35: "unschaerfe",
    36: "unschaerfe",
    37: "referenz",
    38: "referenz",
    # Bänder 39-44, Schema 2.2.0 (W7.1) - Schnittstelle §2: "rolle =
    # bedingung (39-41) bzw. aggregat_kategorie (42-44)".
    39: "bedingung",
    40: "bedingung",
    41: "bedingung",
    42: "aggregat_kategorie",
    43: "aggregat_kategorie",
    44: "aggregat_kategorie",
}

# Familie/Stufe je Band, Schema 2.2.0 (W7.1) - schnittstelle-manifest-2.2.md
# §2, wortgleich übernommen. Reihenfolge wie BAND_NAMES.
EXPECTED_FAMILIE_BY_NAME = {
    "official_settlement_source": "siedlung",
    "settlement_buffer": "siedlung",
    "haeuser_im_gruenen_ferienhaus": "haeuser_im_gruenen",
    "haeuser_im_gruenen_widmung": "haeuser_im_gruenen",
    "haeuser_im_gruenen_streusiedlung": "haeuser_im_gruenen",
    "haeuser_im_gruenen_noe_pdf": "haeuser_im_gruenen",
    "haeuser_im_gruenen": "haeuser_im_gruenen",
    "nonresidential_hulls_source": "nichtwohn_huellen",
    "nonresidential_hulls_buffer": "nichtwohn_huellen",
    "cableway_buildings_source": "seilbahn_gebaeude",
    "cableway_buildings_buffer": "seilbahn_gebaeude",
    "general_buildings_source": "gebaeude",
    "general_buildings_buffer": "gebaeude",
    "road_motorway_trunk": "verkehr",
    "road_federal_state": "verkehr",
    "rail_main": "verkehr",
    "cableway_people_150m": "verkehr",
    "military_restricted_area": "militaer",
    "airport_area_major": "luftfahrt",
    "airport_runway_corridor_5km": "luftfahrt",
    "nature_protection_areas": "schutzgebiet",
    "osm_nature_protection_areas": "schutzgebiet",
    "geography_slope_too_steep": "kriterien",
    "geography_elevation_too_high": "kriterien",
    "geography_wind_too_low": "kriterien",
    "geography_water_bodies": "kriterien",
    "exclusion_human": "summe",
    "exclusion_nature": "summe",
    "exclusion_geography": "summe",
    "all_exclusions": "ergebnis",
    "available_after_all_exclusions_raw": "ergebnis",
    "available_cleaned_min_10ha": "ergebnis",
    "available_blur_sigma_100m": "ergebnis",
    "available_blur_sigma_200m": "ergebnis",
    "available_blur_sigma_250m": "ergebnis",
    "available_blur_sigma_300m": "ergebnis",
    "official_wind_zoning": "amtliche_zonen",
    "wka_bestand_ausserhalb_zonen": "wka_bestand",
    "haeuser_im_gruenen_source": "haeuser_im_gruenen",
    "general_buildings_roh_osm": "gebaeude",
    "general_buildings_roh_dkm": "gebaeude",
    "sources_human": "summe",
    "sources_nature": "summe",
    "sources_geography": "summe",
}

EXPECTED_STUFE_BY_NAME = {
    "official_settlement_source": "quelle",
    "settlement_buffer": "zone",
    "haeuser_im_gruenen_ferienhaus": "quelle",
    "haeuser_im_gruenen_widmung": "quelle",
    "haeuser_im_gruenen_streusiedlung": "quelle",
    "haeuser_im_gruenen_noe_pdf": "quelle",
    "haeuser_im_gruenen": "zone",
    "nonresidential_hulls_source": "quelle",
    "nonresidential_hulls_buffer": "zone",
    "cableway_buildings_source": "quelle",
    "cableway_buildings_buffer": "zone",
    "general_buildings_source": "quelle",
    "general_buildings_buffer": "zone",
    "road_motorway_trunk": "zone",
    "road_federal_state": "zone",
    "rail_main": "zone",
    "cableway_people_150m": "zone",
    "military_restricted_area": "zone",
    "airport_area_major": "zone",
    "airport_runway_corridor_5km": "zone",
    "nature_protection_areas": "zone",
    "osm_nature_protection_areas": "zone",
    "geography_slope_too_steep": "zone",
    "geography_elevation_too_high": "zone",
    "geography_wind_too_low": "zone",
    "geography_water_bodies": "zone",
    "exclusion_human": "summe_zonen",
    "exclusion_nature": "summe_zonen",
    "exclusion_geography": "summe_zonen",
    "all_exclusions": "summe_zonen",
    "available_after_all_exclusions_raw": "ergebnis",
    "available_cleaned_min_10ha": "ergebnis",
    "available_blur_sigma_100m": "ergebnis",
    "available_blur_sigma_200m": "ergebnis",
    "available_blur_sigma_250m": "ergebnis",
    "available_blur_sigma_300m": "ergebnis",
    "official_wind_zoning": "zone",
    "wka_bestand_ausserhalb_zonen": "zone",
    "haeuser_im_gruenen_source": "aggregat",
    "general_buildings_roh_osm": "roh",
    "general_buildings_roh_dkm": "roh",
    "sources_human": "summe_quellen",
    "sources_nature": "summe_quellen",
    "sources_geography": "summe_quellen",
}

# dashboard_layer ist false nur für die vier Unschärfebänder 33-36
# (Schnittstelle §1).
NON_DASHBOARD_LAYER_NAMES = {
    "available_blur_sigma_100m",
    "available_blur_sigma_200m",
    "available_blur_sigma_250m",
    "available_blur_sigma_300m",
}

# Die transitive Ausbreitung der geography_water_bodies-Abweichung
# (PLAN.md §13.9/Regel 8), vorher berechnet aus compose_exclusion_geotiff()s
# tatsächlicher Verschaltung (geography_water_bodies -> exclusion_geography
# -> all_exclusions -> available_after_all_exclusions_raw -> sowohl
# available_cleaned_min_10ha als auch die vier Blur-Bänder, die laut
# pipeline/finalize.py mit blur_source="raw" von available_after_all_
# exclusions_raw abhängen, nicht von available_cleaned). Neun Bänder -
# dieselbe Zahl, die der Bericht zu W3.1 vorab nennt.
# Seit Schema 2.2.0 (W7.1) zehn statt neun Bänder: sources_geography (44)
# hängt laut Schnittstelle §2 ebenfalls von geography_water_bodies ab (Σ
# Quellen Geografie) und wird deshalb vom selben transitiven Abschluss
# erreicht - ans Ende der Liste, weil Index 44 der höchste im Raster ist.
EXPECTED_WATER_BODIES_IMPACT_PATH = [
    "geography_water_bodies",
    "exclusion_geography",
    "all_exclusions",
    "available_after_all_exclusions_raw",
    "available_cleaned_min_10ha",
    "available_blur_sigma_100m",
    "available_blur_sigma_200m",
    "available_blur_sigma_250m",
    "available_blur_sigma_300m",
    "sources_geography",
]

# Die transitive Ausbreitung der zweiten §13.9-Ursache (Punkt 34, Wegfall
# adressloser DKM-Großflächen, Paket W5.P2) - Schema 2.1.0, W5.P5. Vorher
# genannt aus der tatsächlichen Verschaltung: Startknotensatz sind alle
# Bänder, deren quelle dkm_geoparquet referenziert
# (haeuser_im_gruenen_streusiedlung, nonresidential_hulls_source,
# cableway_buildings_source, general_buildings_source - letzteres über
# BAND_SOURCES, erstere drei über die HIG-Zwischenschicht hig_hulls_source/
# OFFICIAL_COVER_LAYERS, siehe Kommentar bei "cableway_buildings_source" in
# BAND_SOURCES), dann derselbe transitive Abschluss über abgeleitet_von wie
# beim Wasserpfad. Überschneidet sich mit EXPECTED_WATER_BODIES_IMPACT_PATH
# an den gemeinsamen Aggregat-/Verfügbarkeitsbändern (all_exclusions u. a.)
# - beide Ursachen überlagern sich dort tatsächlich (siehe
# docs/rewrite/abweichungen.tsv, Bänder 30-36).
# Seit Schema 2.2.0 (W7.1) 19 statt 16 Bänder: general_buildings_roh_dkm (41)
# ist ein neuer Startknoten (seine quelle enthält dkm_geoparquet direkt,
# siehe BAND_SOURCES), haeuser_im_gruenen_source (39) und sources_human (42)
# werden über ihr abgeleitet_von erreicht (hängen an
# haeuser_im_gruenen_streusiedlung bzw. general_buildings_source/
# cableway_buildings_source, beides bereits reachte Bänder) - alle drei in
# Index-Reihenfolge ans Ende gehängt.
EXPECTED_DKM_GEOPARQUET_IMPACT_PATH = [
    "haeuser_im_gruenen_streusiedlung",
    "haeuser_im_gruenen",
    "nonresidential_hulls_source",
    "nonresidential_hulls_buffer",
    "cableway_buildings_source",
    "cableway_buildings_buffer",
    "general_buildings_source",
    "general_buildings_buffer",
    "exclusion_human",
    "all_exclusions",
    "available_after_all_exclusions_raw",
    "available_cleaned_min_10ha",
    "available_blur_sigma_100m",
    "available_blur_sigma_200m",
    "available_blur_sigma_250m",
    "available_blur_sigma_300m",
    "haeuser_im_gruenen_source",
    "general_buildings_roh_dkm",
    "sources_human",
]


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


def test_band_count_is_44(manifest):
    assert manifest["band_count"] == 44
    assert len(manifest["bands"]) == 44


def test_band_names_and_order_match_input(manifest):
    assert [b["name"] for b in manifest["bands"]] == BAND_NAMES
    assert [b["index"] for b in manifest["bands"]] == list(range(1, 45))


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
    assert manifest["schema_version"] == "2.2.0"
    assert manifest["pipeline"] == "widmung_v2"
    assert manifest["band_schema"] == "clean-44-ohne-wichtige-objekte-aug-2026"
    assert manifest["raster_file"] == "osm_wka_distance_zones_widmung_v2.tif"
    assert manifest["generated_at"].endswith("Z")


def test_stufe_order_top_level_field(manifest):
    assert manifest["stufe_order"] == [
        "roh",
        "quelle",
        "aggregat",
        "zone",
        "summe_quellen",
        "summe_zonen",
        "ergebnis",
    ]


def test_familien_top_level_field(manifest):
    familien = manifest["familien"]
    assert len(familien) == 16
    for f in familien:
        assert set(f.keys()) == {"key", "category", "label_de"}
    # "summe" kommt bewusst dreimal vor - je Kategorie Mensch/Natur/Geografie.
    summe_categories = [f["category"] for f in familien if f["key"] == "summe"]
    assert summe_categories == ["Mensch", "Natur", "Geografie"]


def test_familie_and_stufe_match_interface_assignment(manifest):
    for band in manifest["bands"]:
        assert band["familie"] == EXPECTED_FAMILIE_BY_NAME[band["name"]], band["name"]
        assert band["stufe"] == EXPECTED_STUFE_BY_NAME[band["name"]], band["name"]
        assert band["stufe"] in manifest["stufe_order"]


def test_dashboard_layer_false_only_for_blur_bands(manifest):
    for band in manifest["bands"]:
        expected = band["name"] not in NON_DASHBOARD_LAYER_NAMES
        assert band["dashboard_layer"] is expected, band["name"]


def test_default_visible_derived_from_stufe(manifest):
    for band in manifest["bands"]:
        expected = band["stufe"] == "zone" or band["name"] == "available_cleaned_min_10ha"
        assert band["default_visible"] is expected, band["name"]


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
    # Band 41 (general_buildings_roh_dkm, Schema 2.2.0/W7.1) neu dazu: exakt
    # dieselben rekonstruierten NÖ-DKM-Polygone wie general_buildings_source.
    assert caveat["affects"]["bands"] == [8, 9, 12, 13, 27, 30, 31, 32, 33, 34, 35, 36, 41]
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


def test_role_matches_expected_bands(manifest):
    for band in manifest["bands"]:
        assert band["rolle"] == EXPECTED_ROLE_BY_INDEX[band["index"]], band["name"]


def test_buffer_m_only_for_bands_with_a_single_austria_wide_value(manifest):
    by_name = {b["name"]: b for b in manifest["bands"]}
    assert by_name["haeuser_im_gruenen"]["puffer_m"] == 750.0
    assert by_name["nonresidential_hulls_buffer"]["puffer_m"] == 25.0
    assert by_name["cableway_buildings_buffer"]["puffer_m"] == 50.0
    assert by_name["general_buildings_buffer"]["puffer_m"] == 25.0
    assert by_name["road_motorway_trunk"]["puffer_m"] == 150.0
    # Bundeslandabhängig - kein einzelner Wert, aber ein erklärender Hinweis.
    assert by_name["settlement_buffer"]["puffer_m"] is None
    assert "1.200 m" in by_name["settlement_buffer"]["puffer_hinweis"]
    # Puffer schon im Quellband enthalten.
    assert by_name["haeuser_im_gruenen_noe_pdf"]["puffer_m"] is None
    assert by_name["haeuser_im_gruenen_noe_pdf"]["puffer_hinweis"]
    # Korridor statt isotropem Puffer.
    assert by_name["airport_runway_corridor_5km"]["puffer_m"] is None
    assert "5.000 m" in by_name["airport_runway_corridor_5km"]["puffer_hinweis"]
    # Reine Quell-/Schwellwert-/Aggregatbänder: weder Wert noch Hinweis.
    for name in ("official_settlement_source", "geography_water_bodies", "all_exclusions"):
        assert by_name[name]["puffer_m"] is None
        assert by_name[name]["puffer_hinweis"] is None


def test_quelle_set_for_condition_bands_empty_for_aggregates(manifest):
    by_name = {b["name"]: b for b in manifest["bands"]}
    assert by_name["geography_water_bodies"]["quelle"] == ["osm_pbf"]
    assert by_name["nature_protection_areas"]["quelle"] == ["naturschutzgebiete"]
    assert by_name["official_settlement_source"]["quelle"]
    # Aggregat-/Ergebnisbänder lesen keine Rohdaten direkt.
    for name in ("exclusion_human", "exclusion_nature", "exclusion_geography", "all_exclusions", "available_after_all_exclusions_raw"):
        assert by_name[name]["quelle"] == [], name


def test_abgeleitet_von_traces_aggregates_to_their_condition_bands(manifest):
    by_name = {b["name"]: b for b in manifest["bands"]}
    assert by_name["exclusion_geography"]["abgeleitet_von"] == [
        "geography_slope_too_steep",
        "geography_elevation_too_high",
        "geography_wind_too_low",
        "geography_water_bodies",
    ]
    assert by_name["all_exclusions"]["abgeleitet_von"] == ["exclusion_human", "exclusion_nature", "exclusion_geography"]
    assert by_name["available_cleaned_min_10ha"]["abgeleitet_von"] == ["available_after_all_exclusions_raw"]
    assert by_name["available_blur_sigma_100m"]["abgeleitet_von"] == ["available_after_all_exclusions_raw"]
    # Bedingungsbänder sind nicht aus anderen Bändern abgeleitet.
    assert by_name["geography_water_bodies"]["abgeleitet_von"] == []


def test_geography_water_bodies_wirkungspfad_is_the_predicted_nine_bands(manifest):
    # PLAN.md §13.9/Regel 8: nur diese neun Bänder dürfen von run1 abweichen
    # (die geography_water_bodies-Korrektur, 543.106 Zellen, ausschließlich
    # zusätzlich). Vorab genannt, nicht nachträglich gepasst.
    assert manifest["geography_water_bodies_wirkungspfad"] == EXPECTED_WATER_BODIES_IMPACT_PATH


def test_dkm_geoparquet_wirkungspfad_is_the_predicted_sixteen_bands(manifest):
    # PLAN.md §13.9/Regel 8, zweite Ursache (Punkt 34, W5.P2/W5.P5): genau
    # diese 16 Bänder dürfen zusätzlich von run1 abweichen. Vorab genannt,
    # nicht nachträglich gepasst - siehe EXPECTED_DKM_GEOPARQUET_IMPACT_PATH.
    assert manifest["dkm_geoparquet_wirkungspfad"] == EXPECTED_DKM_GEOPARQUET_IMPACT_PATH


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
    assert loaded["band_count"] == 44
    assert [b["name"] for b in loaded["bands"]] == BAND_NAMES
    assert loaded["parameters"] == TAGS
