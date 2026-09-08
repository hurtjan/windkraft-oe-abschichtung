"""Tests für calc.viz.band_metadata: Kategorien, Farben, Default-Sichtbarkeit.

Regressionsschutz für die Reihenfolge von HUMAN_PREFIXES (siehe Modul-Docstring
von band_metadata.py) und für die Farb-/Kategorie-Zuordnung der 38 Bänder des
Clean-Schemas.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc.viz.band_metadata import (  # noqa: E402
    CATEGORY_ORDER,
    DEFAULT_VISIBLE,
    HUMAN_PREFIXES,
    categorize_layer,
    layer_color,
)

# Die 38 Bänder des aktuellen Clean-Schemas, in Bandreihenfolge.
BAND_NAMES = [
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

# Referenzkategorie laut CATEGORY_ORDER, nicht hart als String-Literal geraten.
REFERENZ_KATEGORIE = CATEGORY_ORDER[5]
assert REFERENZ_KATEGORIE == "Referenz (Zonen & WKA-Bestand)"

EXPECTED_CATEGORY = (
    ["Mensch"] * 20
    + ["Natur"] * 2
    + ["Geografie"] * 4
    + ["Mensch"]
    + ["Natur"]
    + ["Geografie"]
    + ["Total & Ergebnis"] * 7
    + [REFERENZ_KATEGORIE] * 2
)
assert len(BAND_NAMES) == 38
assert len(EXPECTED_CATEGORY) == 38


def test_categorize_layer_matches_expected_mapping():
    for name, expected in zip(BAND_NAMES, EXPECTED_CATEGORY):
        category, _is_total = categorize_layer(name)
        assert category == expected, f"{name}: expected {expected!r}, got {category!r}"


def test_human_prefixes_ordering_regression():
    # HUMAN_PREFIXES ist ein geordnetes Tuple, kein set/frozenset: Sortieren
    # oder in ein set konvertieren würde die Prüfreihenfolge zerstören und
    # könnte Bänder stillschweigend falsch kategorisieren (der Kommentar im
    # Quellmodul warnt ausdrücklich davor, dass official_settlement_/
    # official_hig_ vor dem generischen official_-Fang stehen müssen).
    assert isinstance(HUMAN_PREFIXES, (list, tuple))
    assert not isinstance(HUMAN_PREFIXES, (set, frozenset))

    assert "official_settlement_" in HUMAN_PREFIXES
    assert "official_" not in HUMAN_PREFIXES  # generic catch-all lives outside HUMAN_PREFIXES
    assert HUMAN_PREFIXES.index("official_settlement_") < len(HUMAN_PREFIXES)

    if "official_hig_" in HUMAN_PREFIXES:
        assert HUMAN_PREFIXES.index("official_hig_") < len(HUMAN_PREFIXES)

    # official_settlement_source must land in Mensch via the specific prefix,
    # not merely coincidentally: it is not caught by any other HUMAN_PREFIXES
    # entry, so this also exercises official_settlement_ specifically.
    category, _ = categorize_layer("official_settlement_source")
    assert category == "Mensch"

    category, _ = categorize_layer("official_hig_something")
    assert category == "Mensch"

    # A name that would ONLY match the generic "official_" catch-all (not
    # part of HUMAN_PREFIXES) must NOT land in Mensch - it lands in the
    # reference category instead. This confirms official_settlement_/
    # official_hig_ are doing real, specific work in HUMAN_PREFIXES.
    category, _ = categorize_layer("official_wind_zoning")
    assert category == "Referenz (Zonen & WKA-Bestand)"


def test_layer_color_all_bands_are_valid_rgba():
    for name in BAND_NAMES:
        color = layer_color(name)
        assert len(color) == 4
        for component in color:
            assert 0 <= component <= 255


def test_layer_color_spot_check_exact_literals():
    # Werte gegen die alte Quelldatei geprüft (windkraft_ö_karten,
    # scripts/webmap/build_osm_wka_layer_viewer.py DEFAULT_COLORS).
    assert tuple(layer_color("official_settlement_source")) == (0, 60, 200, 200)
    assert tuple(layer_color("all_exclusions")) == (255, 0, 0, 120)
    assert tuple(layer_color("available_cleaned_min_10ha")) == (0, 255, 0, 185)


def test_default_visible():
    # DEFAULT_VISIBLE ist im migrierten Modul ein set.
    assert isinstance(DEFAULT_VISIBLE, set)
    assert DEFAULT_VISIBLE == {"all_exclusions", "available_cleaned_min_10ha"}
