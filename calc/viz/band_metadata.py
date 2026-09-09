"""Bandmetadaten (Farbe, Kategorie, Default-Sichtbarkeit) für GeoTIFF-Bänder.

Dies ist die eine gemeinsame Quelle für Farben, Kategorien und
Default-Sichtbarkeit, die sich Manifest-Writer und Viewer teilen. Der Inhalt
wurde übernommen aus ``build_osm_wka_layer_viewer.py`` des alten Repos
(``windkraft_ö_karten``, ``scripts/webmap/``), reduziert auf die 38 Bänder des
aktuellen Clean-Schemas (Legacy-Bandnamen aus früheren Schemata wurden
weggelassen).

Wichtig: Die Reihenfolge von ``HUMAN_PREFIXES`` ist bedeutsam und darf nicht
achtlos verändert werden - ``official_settlement_`` und ``official_hig_``
müssen vor dem generischen ``official_``-Fang (Amtliche Zonen) geprüft
werden, da sie Mensch-Quellbänder sind, keine Referenzlayer.
"""

from __future__ import annotations

DEFAULT_COLORS = {
    "official_settlement_source": [0, 60, 200, 200],
    "settlement_buffer": [70, 130, 220, 140],
    "haeuser_im_gruenen_ferienhaus": [155, 30, 90, 200],
    "haeuser_im_gruenen_widmung": [230, 120, 0, 200],
    "haeuser_im_gruenen_streusiedlung": [255, 170, 0, 190],
    "haeuser_im_gruenen_noe_pdf": [255, 210, 60, 110],
    "haeuser_im_gruenen": [255, 140, 60, 150],
    "airport_area_major": [255, 0, 0, 140],
    "airport_runway_corridor_5km": [255, 0, 255, 110],
    # Bestands-WKA außerhalb amtlicher Zonen: Türkis, klar getrennt vom Blau
    # der amtlichen Zonen - beides Referenzlayer, keine Ausschlüsse.
    "wka_bestand_ausserhalb_zonen": [0, 190, 230, 200],
    "nonresidential_hulls_source": [130, 130, 130, 190],
    "nonresidential_hulls_buffer": [180, 180, 180, 130],
    "cableway_buildings_source": [0, 130, 130, 190],
    "cableway_buildings_buffer": [80, 190, 190, 150],
    "general_buildings_source": [150, 60, 200, 190],
    "general_buildings_buffer": [180, 120, 220, 150],
    "road_motorway_trunk": [255, 140, 0, 150],
    "road_federal_state": [255, 180, 0, 145],
    "rail_main": [120, 80, 40, 150],
    "cableway_people_150m": [255, 0, 0, 140],
    "military_restricted_area": [255, 0, 0, 140],
    "nature_protection_areas": [0, 170, 60, 170],
    "osm_nature_protection_areas": [255, 0, 0, 140],
    "geography_slope_too_steep": [120, 70, 30, 150],
    "geography_elevation_too_high": [120, 120, 120, 150],
    "geography_wind_too_low": [80, 160, 255, 145],
    "geography_water_bodies": [0, 90, 170, 170],
    "exclusion_human": [255, 0, 0, 130],
    "exclusion_nature": [0, 180, 0, 150],
    "exclusion_geography": [80, 80, 220, 140],
    "all_exclusions": [255, 0, 0, 120],
    "available_after_all_exclusions_raw": [0, 220, 120, 150],
    "available_cleaned_min_10ha": [0, 255, 0, 185],
    "official_wind_zoning": [0, 90, 255, 190],
    # Bänder 39-44, Schema 2.2.0 (W7.1). Farbe ist ausdrücklich Kosmetik
    # (siehe Auftrag) - hier je Familie derselbe Grundton wie das
    # zugehörige Quell-/Zonenband, nur etwas heller/blasser für die neue
    # roh/aggregat/summe_quellen-Stufe. TODO(W7.x): Helligkeit systematisch
    # nach `stufe` abstufen (z. B. eine Funktion über STUFE_ORDER in
    # calc/band_manifest.py), statt jede Farbe einzeln von Hand zu setzen.
    "haeuser_im_gruenen_source": [255, 150, 90, 160],
    "general_buildings_roh_osm": [190, 130, 220, 150],
    "general_buildings_roh_dkm": [170, 100, 210, 150],
    "sources_human": [255, 90, 90, 110],
    "sources_nature": [90, 200, 90, 110],
    "sources_geography": [110, 140, 220, 110],
}

GEO_WIND_COLOR = [80, 160, 255, 145]
CLEANED_ZONE_COLOR = [0, 255, 0, 185]
FALLBACK_COLOR = [255, 0, 0, 140]

# Glättungsvarianten (available_blur_sigma_*): eine geordnete Reihe, deshalb
# ein Farbton hell -> dunkel mit steigendem Sigma statt vier bunter Farben.
# Ohne diese Regel fielen alle vier auf FALLBACK_COLOR (reinrot) - untereinander
# ununterscheidbar und mit Ausschlussflächen verwechselbar.
BLUR_SIGMA_COLORS = {
    "100m": [134, 226, 168, 180],
    "200m": [45, 190, 130, 180],
    "250m": [0, 148, 110, 180],
    "300m": [0, 104, 88, 180],
}


def layer_color(name: str) -> list[int]:
    """Color for a band name, with prefix fallbacks for parameterized bands."""
    if name in DEFAULT_COLORS:
        return DEFAULT_COLORS[name]
    if name.startswith("geo_wind_below_"):
        return GEO_WIND_COLOR
    if name.startswith("available_cleaned_min_"):
        return CLEANED_ZONE_COLOR
    if name.startswith("available_blur_sigma_"):
        return BLUR_SIGMA_COLORS.get(name.rsplit("_", 1)[-1], CLEANED_ZONE_COLOR)
    if name.startswith("settlement_cluster_buffer_"):
        return DEFAULT_COLORS["settlement_cluster_buffer"]
    if name.startswith("settlement_v2_buffer_"):
        return DEFAULT_COLORS["settlement_v2_buffer"]
    if name.startswith("settlement_buffer_"):
        return DEFAULT_COLORS["settlement_buffer"]
    if name.startswith("exclusion_human_"):
        return DEFAULT_COLORS["exclusion_human"]
    if name.startswith("available_after_all_exclusions_raw_"):
        return DEFAULT_COLORS["available_after_all_exclusions_raw"]
    return FALLBACK_COLOR


# Panel categories: each layer is sorted into one section; the category's
# aggregate band ("total") is rendered bold at the end of its section.
CATEGORY_ORDER = ["Mensch", "Natur", "Geografie", "Total & Ergebnis", "Siedlungsabstand-Varianten", "Referenz (Zonen & WKA-Bestand)", "Sonstige"]

# Bands carrying one of these suffixes belong to a settlement-buffer variant
# (buffer / human total / raw / cleaned) and get their own panel section.
VARIANT_SUFFIXES = ("_default", "_800m", "_1000m", "_1200m", "_1500m", "_2000m")

CATEGORY_TOTALS = {
    "exclusion_human": "Mensch",
    "tot_exclusion_human": "Mensch",
    "exclusion_nature": "Natur",
    "tot_exclusion_nature": "Natur",
    "exclusion_geography": "Geografie",
    "tot_exclusion_geography": "Geografie",
    "all_exclusions": "Total & Ergebnis",
    "tot_exclusion_all": "Total & Ergebnis",
    # Bänder 42-44, Schema 2.2.0 (W7.1): Σ Quellen je Kategorie, dieselbe
    # is_total-Behandlung (fett am Ende der Sektion) wie die Σ-Zonen-Bänder.
    "sources_human": "Mensch",
    "sources_nature": "Natur",
    "sources_geography": "Geografie",
}

# official_settlement_/official_hig_ MÜSSEN vor dem generischen "official_"-Fang
# (Amtliche Zonen) geprüft werden - sie sind Mensch-Quellbänder der v2-Pipeline.
HUMAN_PREFIXES = ("settlement_", "greenland_", "haeuser_im_gruenen", "important_objects_", "cableway_buildings_", "general_buildings_", "power_", "road_", "rail_", "cableway_", "military_", "airport_", "human_", "official_settlement_", "official_hig_", "ferienhaus_", "hig_hulls_", "noe_pdf_", "bewohnt_", "nonresidential_")
NATURE_PREFIXES = ("nature_", "osm_nature_")
GEO_PREFIXES = ("geography_", "geo_")
RESULT_PREFIXES = ("available_", "cleaned_")


def categorize_layer(name: str) -> tuple[str, bool]:
    """Return (category, is_total) for a band name."""
    if name in CATEGORY_TOTALS:
        return CATEGORY_TOTALS[name], True
    if name.endswith(VARIANT_SUFFIXES):
        return "Siedlungsabstand-Varianten", False
    if name.startswith(HUMAN_PREFIXES):
        return "Mensch", False
    if name.startswith(NATURE_PREFIXES):
        return "Natur", False
    if name.startswith(GEO_PREFIXES):
        return "Geografie", False
    if name.startswith(RESULT_PREFIXES):
        return "Total & Ergebnis", False
    if name.startswith(("official_", "wka_")):
        return "Referenz (Zonen & WKA-Bestand)", False
    return "Sonstige", False


# Seit Schema 2.2.0 (W7.1) NICHT mehr die Quelle für band["default_visible"]
# im Manifest - das leitet calc.band_manifest.band_default_visible() jetzt
# aus der Stufe ab (zone + available_cleaned_min_10ha). Diese Konstante
# bleibt unverändert stehen (additiv, kein bestehendes Feld verschwindet)
# und wird von tests/test_band_metadata.py weiter geprüft.
DEFAULT_VISIBLE = {"all_exclusions", "available_cleaned_min_10ha"}
