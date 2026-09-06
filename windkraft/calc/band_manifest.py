"""Band-Manifest: Sidecar-JSON neben dem finalen Widmung-v2-GeoTIFF.

Geschrieben direkt nach ``compose_exclusion_geotiff()`` aus genau den beiden
Werten, die dort ohnehin schon feststehen: der geschriebenen Bandnamenliste
und dem Tag-Dict, das in die Datei gestempelt wird. Das Manifest erfindet
nichts nach und liest das fertige Raster nicht erneut - Bandzahl, -namen und
-reihenfolge sind damit per Konstruktion identisch mit dem TIF.

Warum überhaupt: Konsumenten (Dashboard, Viewer) lösen Bänder über den NAMEN
auf und brechen bei unbekanntem Namen oder falscher Bandzahl hart ab. Zwei
Tatsachen, die bisher nur implizit existierten, werden hier explizit:

  ``value_type``          bisher nur daran erkennbar, dass die vier
                          ``available_blur_sigma_*``-Bänder als einzige einen
                          Band-Tag ``UNIT=percent_0_100`` tragen
                          (``abschichtung_common.py``, ``update_tags`` im
                          Blur-Zweig von ``compose_exclusion_geotiff``); alle
                          übrigen Bänder sind 0/1.
  ``clipped_to_austria``  bisher Stammeswissen in einem Docstring von
                          ``scripts/analysis/build_v2_dashboard_data.py``.
                          Maßgeblich ist der Code: in
                          ``compose_exclusion_geotiff()`` werden die
                          Aggregat-/Ergebnisbänder mit ``& valid_area``
                          verschnitten, die Bedingungs- und Referenzbänder
                          nicht.

Farben, Kategorien, ``is_total`` und ``default_visible`` kommen aus
``windkraft/viz/band_metadata.py`` - der gemeinsamen Quelle von Viewer und
Manifest. Hier werden sie NICHT dupliziert.

Stil (JSON-Einrückung, Zeitstempel, Schlüsselreihenfolge) folgt bewusst
``write_legend()`` in ``windkraft/calc/kataster_layers.py`` des Alt-Repos.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from windkraft.viz.band_metadata import (
    CATEGORY_ORDER,
    DEFAULT_VISIBLE,
    categorize_layer,
    layer_color,
)

SCHEMA_VERSION = "1.0.0"
MANIFEST_SUFFIX = ".bands.json"

# Fallbacks, falls die Tags einmal ohne diese Schlüssel kommen. Der Regelfall
# ist, dass PIPELINE/BAND_SCHEMA aus dem tags-Dict stammen - dann steht im
# Manifest garantiert dasselbe wie in den Datei-Tags des TIFs.
DEFAULT_PIPELINE = "widmung_v2"
DEFAULT_BAND_SCHEMA = "clean-38-ohne-wichtige-objekte-aug-2026"

# Wie output_profile() in windkraft/calc/abschichtung_common.py das GeoTIFF
# anlegt. Hier als Konstante gespiegelt statt importiert, damit dieses Modul
# ohne rasterio/geopandas testbar bleibt.
RASTER_DTYPE = "uint8"
RASTER_NODATA = 0
NODATA_MEANING = (
    "0 ist ein gueltiger Wert (Bedingung trifft nicht zu), kein echtes NoData"
)

# Die vier Unschärfebänder sind die einzigen Nicht-0/1-Bänder; sie tragen im
# TIF den Band-Tag UNIT=percent_0_100.
PERCENT_BAND_PREFIX = "available_blur_sigma_"

VALUE_TYPE_BINARY = "binary"
VALUE_TYPE_PERCENT = "percent_0_100"

# Bänder, die compose_exclusion_geotiff() mit `& valid_area` auf das
# Staatsgebiet schneidet (Aggregate, Ergebnis, Unschärfe). Die Bedingungsbänder
# 1-26 und die Referenzbänder 37-38 laufen über die volle Bounding Box.
# Anmerkung zur Unschärfe: ihre Basis (available_after_all_exclusions_raw) ist
# geschnitten, die Gauß-Glättung selbst wird danach nicht erneut maskiert - der
# Zuschnitt ist also geerbt, nicht nachträglich erzwungen.
CLIPPED_EXACT = {
    "exclusion_human",
    "exclusion_nature",
    "exclusion_geography",
    "all_exclusions",
    "available_after_all_exclusions_raw",
}
CLIPPED_PREFIXES = (
    "exclusion_human_",
    "exclusion_nature_",
    "exclusion_geography_",
    "all_exclusions_",
    "available_after_all_exclusions_raw_",
    "available_cleaned_min_",
    PERCENT_BAND_PREFIX,
)

# --------------------------------------------------------------------------
# Kurzlabels für die Legende. Für die Bedingungsbänder 1-26 stammen die langen
# Beschreibungen aus Band.description im Skript; hier steht bewusst nur der
# knappe Legendentext. Zwölf Labels sind aus EXCLUSION_LAYERS in
# scripts/analysis/build_v2_dashboard_data.py übernommen, die dortigen
# Pufferangaben wurden gegen den Code korrigiert.
# --------------------------------------------------------------------------
LABELS_DE = {
    "official_settlement_source": "Amtliches Wohnbauland (Quelle)",
    "settlement_buffer": "Siedlungsabstand (NÖ 1.200 m, sonst 1.000 m)",
    "haeuser_im_gruenen_ferienhaus": "Ferienhaus / Tourismus (Quelle)",
    "haeuser_im_gruenen_widmung": "Amtliche HiG-Widmung (Quelle, ohne NÖ)",
    "haeuser_im_gruenen_streusiedlung": "Streusiedlungs-Hüllen (Quelle, ohne NÖ)",
    "haeuser_im_gruenen_noe_pdf": "NÖ-SekROP-750-m-Zonen",
    "haeuser_im_gruenen": "Häuser im Grünen (750 m)",
    "nonresidential_hulls_source": "Nicht-Wohn-Hüllen (Quelle)",
    "nonresidential_hulls_buffer": "Nicht-Wohn-Hülle (25 m)",
    "cableway_buildings_source": "Seilbahn-Gebäude (Quelle)",
    "cableway_buildings_buffer": "Seilbahn-Gebäude (50 m)",
    "general_buildings_source": "Sonstige Gebäude + Einzellagen (Quelle)",
    "general_buildings_buffer": "Sonstige Gebäude (25 m)",
    "road_motorway_trunk": "Autobahn / Schnellstraße (150 m)",
    "road_federal_state": "Bundes- / Landesstraße (150 m)",
    "rail_main": "Hauptbahn (150 m)",
    "cableway_people_150m": "Personenseilbahn (150 m)",
    "military_restricted_area": "Militärisches Sperrgebiet",
    "airport_area_major": "Hauptflughafen-Areal",
    "airport_runway_corridor_5km": "An-/Abflugkorridor (5 km)",
    "nature_protection_areas": "Naturschutzgebiete (amtlich)",
    "osm_nature_protection_areas": "Naturschutzgebiete (OSM)",
    "geography_slope_too_steep": "Hangneigung zu steil",
    "geography_elevation_too_high": "Seehöhe zu hoch",
    "geography_wind_too_low": "Windhöffigkeit zu gering",
    "geography_water_bodies": "Größere Gewässer",
    "exclusion_human": "Σ Ausschluss Mensch",
    "exclusion_nature": "Σ Ausschluss Natur",
    "exclusion_geography": "Σ Ausschluss Geografie",
    "all_exclusions": "Σ Ausschluss gesamt",
    "available_after_all_exclusions_raw": "Verfügbare Fläche, roh",
    "official_wind_zoning": "Amtliche Windkraft-Zonen",
    "wka_bestand_ausserhalb_zonen": "WKA-Bestand außerhalb der Zonen",
}

# --------------------------------------------------------------------------
# Beschreibungen der Bänder 27-38. Die der Bänder 1-26 kommen zur Laufzeit aus
# Band.description in scripts/widmung_v2/04_create_distance_zones.py; die hier
# sind aus docs/widmung_v2.md (Abschnitte "Aggregate und Ergebnis",
# "Unsicherheits-Bänder", "Referenzbänder") portiert.
# --------------------------------------------------------------------------
DESCRIPTIONS_DE = {
    "exclusion_human": (
        "ODER-Verknüpfung aller Mensch-Ausschlüsse (Bänder 2, 7, 9, 11, 13, 14-20), "
        "auf das Staatsgebiet zugeschnitten."
    ),
    "exclusion_nature": "ODER der Natur-Bänder (21-22), auf das Staatsgebiet zugeschnitten.",
    "exclusion_geography": "ODER der Geografie-Bänder (23-26), auf das Staatsgebiet zugeschnitten.",
    "all_exclusions": "ODER von 27-29: alles, was ausgeschlossen ist.",
    "available_after_all_exclusions_raw": (
        "Das Negativ von all_exclusions - verfügbare Fläche ohne Mindestgrößen-Filter."
    ),
}


def _cleaned_description(name: str) -> str:
    ha = name[len("available_cleaned_min_"):].removesuffix("ha")
    return (
        f"Das Endergebnis: die rohe verfügbare Fläche, bereinigt um Splitter - nur "
        f"zusammenhängende Flächen ab {ha} ha (4er-Nachbarschaft)."
    )


def _sigma_text(name: str) -> str:
    """"100m" -> "100 m" - der Bandname kennt kein Leerzeichen, die Legende schon."""
    return name[len(PERCENT_BAND_PREFIX):].removesuffix("m") + " m"


def _blur_description(name: str) -> str:
    sigma = _sigma_text(name)
    return (
        f"Gauß-geglättete Eignungsfläche (Werte 0-100 %): der gewichtete Anteil "
        f"verfügbarer Fläche in der Umgebung jeder Zelle, Glättungsradius Sigma "
        f"{sigma}. Basis ist die ROHE verfügbare Fläche, daher sind auch Flächen "
        f"unter der Mindestgrößen-Schwelle sichtbar. 100 = tief in einer großen "
        f"Zone, ~50 = an der Kante, schmale Splitter verwaschen."
    )


DESCRIPTIONS_DE_TRAILING = {
    "official_wind_zoning": (
        "Alle amtlichen Windkraft-Positivzonen der Länder in einem Band: NÖ Zonierung "
        "(71 Zonen, LGBl. 47/2024), Steiermark SAPRO Vorrang-/Eignungszonen, Salzburg "
        "Vorrangzonen, Burgenland Eignungszonen, Kärnten RED-III-Beschleunigungszonen. "
        "Dient dem Soll-Ist-Vergleich mit der Abschichtung, ist selbst kein Ausschluss."
    ),
    "wka_bestand_ausserhalb_zonen": (
        "Bestehende Windräder aus OSM, die AUSSERHALB der amtlichen Zonen stehen, zu "
        "Park-Hüllen zusammengefasst (Anlagen mit < 750 m Abstand bilden einen Park; "
        "konvexe Hülle + 200 m Rand). Referenzband, kein Ausschluss."
    ),
}

# --------------------------------------------------------------------------
# Quellen. Pfade und Stand-Angaben stammen aus data/README.md (§2, §3.1-§3.3)
# bzw. config.json; nichts hier ist geraten. Datensätze, für die dort weder
# Pfad noch Stand belegt sind, fehlen bewusst.
# --------------------------------------------------------------------------
SOURCES = {
    "dgm_25m": {
        "pfad": "data/DGM_R25.tif",
        "stand": "30.03.2026",
        "rolle": "Grid-Template (CRS/Transform), Hangneigung und Seehöhe",
    },
    "wind_leistungsdichte_150m": {
        "pfad": "data/AUT_power-density_150m.tif",
        "stand": "29.03.2026",
        "rolle": "Global Wind Atlas, Windhöffigkeitsschwelle",
    },
    "osm_pbf": {
        "pfad": "data/austria-260330.osm.pbf",
        "stand": "30.03.2026",
        "rolle": "Geofabrik-Extrakt Österreich: Straßen, Bahn, Seilbahnen, Militär, "
                 "Flughäfen, Gebäude, Gewässer, Schutzgebiete, Bestands-WKA",
    },
    "verwaltungsgrenzen_vgd": {
        "pfad": "data/admin_boundaries/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp",
        "stand": "02.10.2022",
        "rolle": "Staatsgebiet (valid_area) und Bundeslandzuordnung",
    },
    "bev_adressregister": {
        "pfad": "data/adressregister/",
        "stand": "Stichtag 01.10.2025",
        "rolle": "Bewohnt-Signal (Adressen und Gebäudeeigenschaften) für die Hüllen-Klassifikation",
    },
    "dkm_geoparquet": {
        "pfad": "output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet",
        "stand": "Dateidatum 15.05.; erzeugtes Artefakt aus BEV-DKM",
        "rolle": "DKM-Bauflächen/Gärten für Streusiedlungs-Hüllen, Nicht-Wohn-Hüllen und Einzellagen",
    },
    "naturschutzgebiete": {
        "pfad": "data/naturschutzgebiete/SG_AT_2024_v_April_Stand_3_April_2024.zip",
        "stand": "03.04.2024",
        "rolle": "Nationalparks, NSG, Europaschutzgebiete/Natura 2000, Ramsar",
    },
    "noe_sekrop_mindestabstandszonen": {
        "pfad": "data/nö_zonierung/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf",
        "stand": "Karten-Stand 02.04.2024 (Dateidatum 29.03.2026)",
        "rolle": "Quelle der NÖ-750-m-Zonen (georeferenziert nach output/noe/pdf_750m_*.geojson)",
    },
    "amtliche_windzonen_noe": {
        "pfad": "data/zonierung_noe.json",
        "stand": "LGBl. 47/2024, 71 Zonen (Dateidatum 30.04.2026)",
        "rolle": "Referenzband official_wind_zoning",
    },
    "amtliche_windzonen_bgld": {
        "pfad": "data/WK_Eignungszonen.zip",
        "stand": "EXPORT_DAT 20260721",
        "rolle": "Referenzband official_wind_zoning",
    },
    "amtliche_windzonen_ktn": {
        "pfad": "data/RED_III_Windkraftbeschleunigungszone.zip",
        "stand": "unbekannt — zu klären",
        "rolle": "Referenzband official_wind_zoning",
    },
    "amtliche_windzonen_stmk_sbg": {
        "pfad": "data/luca_zonen/Stmk.shp, data/luca_zonen/Sbg.shp",
        "stand": "unbekannt — zu klären (handdigitalisiert, nicht amtlich bezogen)",
        "rolle": "Referenzband official_wind_zoning",
    },
    "flaechenwidmung_bgld": {
        "pfad": "data/flächenwidmungen/WIDMUNGSFLAECHEN.zip",
        "stand": "Dateidatum 22.06.",
        "rolle": "Amtliche Flächenwidmung Burgenland",
    },
    "flaechenwidmung_ktn": {
        "pfad": "data/new_widmungs_data/kaernten/flawi_ktn_gpkg.zip",
        "stand": "Dateidatum 12.07.",
        "rolle": "Amtliche Flächenwidmung Kärnten",
    },
    "flaechenwidmung_noe": {
        "pfad": "data/new_widmungs_data/niederoesterreich/RRU_WI_HUELLE.gpkg",
        "stand": "Dateidatum 10.07.",
        "rolle": "Amtliche Flächenwidmung Niederösterreich",
    },
    "flaechenwidmung_ooe": {
        "pfad": "data/new_widmungs_data/oberoesterreich/FLWI_WIDMUNGEN_F.zip",
        "stand": "Dateidatum 10.07.",
        "rolle": "Amtliche Flächenwidmung Oberösterreich",
    },
    "flaechenwidmung_sbg": {
        "pfad": "data/new_widmungs_data/salzburg/Flaechenwidmung_Shapefile.zip",
        "stand": "Dateidatum 12.07.",
        "rolle": "Amtliche Flächenwidmung Salzburg",
    },
    "flaechenwidmung_stmk": {
        "pfad": "data/new_widmungs_data/steiermark/Bauland.zip + data/flächenwidmungen/Flaewi.shp.zip",
        "stand": "Dateidatum 10.07. / 22.06.",
        "rolle": "Amtliche Flächenwidmung Steiermark (beide Dateien nötig)",
    },
    "flaechenwidmung_tirol": {
        "pfad": "data/new_widmungs_data/tirol/FLW_Flaechenwidmung_*.gpkg",
        "stand": "Dateidatum 12.07.",
        "rolle": "Amtliche Flächenwidmung Tirol",
    },
    "flaechenwidmung_vbg": {
        "pfad": "data/new_widmungs_data/vorarlberg/fwp_flaeche.gpkg",
        "stand": "Dateidatum 12.07.",
        "rolle": "Amtliche Flächenwidmung Vorarlberg",
    },
    "flaechenwidmung_wien": {
        "pfad": "data/new_widmungs_data/wien/genflwidmung_wien.geojson",
        "stand": "Dateidatum 29.07.",
        "rolle": "Amtliche Flächenwidmung Wien (WFS GENFLWIDMUNGOGD)",
    },
}

# --------------------------------------------------------------------------
# Caveats. Strukturiert, nicht als Fließtext - Konsumenten sollen die
# betroffenen Bänder maschinell auflösen können.
#
# NÖ-DKM: Für Niederösterreich gibt es keine amtlich flächige DKM-Lieferung,
# die Polygone sind aus DXF-Linienwerk polygonisiert und per Mehrheitsabstimmung
# klassifiziert (data/README.md §4.1). Betroffen sind genau die Bänder, in
# deren Fläche NÖ-DKM-Polygone tatsächlich eingehen - siehe _noe_dkm_affected().
# --------------------------------------------------------------------------
NOE_DKM_AFFECTED_EXACT = {
    "nonresidential_hulls_source",
    "nonresidential_hulls_buffer",
    "general_buildings_source",
    "general_buildings_buffer",
    "exclusion_human",
    "all_exclusions",
    "available_after_all_exclusions_raw",
}
NOE_DKM_AFFECTED_PREFIXES = (
    "exclusion_human_",
    "all_exclusions_",
    "available_after_all_exclusions_raw_",
    "available_cleaned_min_",
    PERCENT_BAND_PREFIX,
)


def _noe_dkm_affected(name: str) -> bool:
    """Hängt dieses Band an den aus DXF rekonstruierten NÖ-DKM-Polygonen?

    Direkt: nonresidential_hulls_source (Hüllenklassen industriegebietartig +
    unbewohnt, NICHT NÖ-maskiert) und general_buildings_source (enthält
    bewohnt_einzellage_source UND ausdrücklich die NÖ-Streusiedlungs-Hüllen,
    siehe scripts/widmung_v2/03_build_osm_layers.py). Dazu deren 25-m-Puffer.

    Geerbt: exclusion_human (ODER über die Pufferbänder), all_exclusions, die
    rohe und bereinigte Verfügbarkeit sowie die daraus geglätteten
    Unschärfebänder.

    Ausdrücklich NICHT betroffen: haeuser_im_gruenen_streusiedlung und das
    Aggregat haeuser_im_gruenen - dort wird NÖ ausmaskiert, den 750-m-Abstand
    trägt in NÖ allein die amtliche SekROP-PDF-Quelle.
    """
    return name in NOE_DKM_AFFECTED_EXACT or name.startswith(NOE_DKM_AFFECTED_PREFIXES)


NOE_DKM_CAVEAT = {
    "id": "noe_dkm_reconstructed",
    "severity": "methodisch",
    "text_de": (
        "Die DKM-Basis für Niederösterreich ist aus DXF-Linienwerk rekonstruiert, "
        "nicht amtlich flächig geliefert. Rund 29 % der rekonstruierten Polygone "
        "sind mehrdeutig klassifiziert oder ohne Klassifikation verworfen."
    ),
    "numbers": {
        "polygons_total": 3491407,
        "ambiguous": 684249,
        "unassigned": 338674,
    },
    "applies_to_other_states": False,
}


# --------------------------------------------------------------------------
# Ableitungen je Band
# --------------------------------------------------------------------------

def band_value_type(name: str) -> str:
    return VALUE_TYPE_PERCENT if name.startswith(PERCENT_BAND_PREFIX) else VALUE_TYPE_BINARY


def band_clipped_to_austria(name: str) -> bool:
    return name in CLIPPED_EXACT or name.startswith(CLIPPED_PREFIXES)


def band_label_de(name: str) -> str:
    if name in LABELS_DE:
        return LABELS_DE[name]
    if name.startswith("available_cleaned_min_"):
        ha = name[len("available_cleaned_min_"):].removesuffix("ha")
        return f"Verfügbare Fläche, bereinigt (≥ {ha} ha)"
    if name.startswith(PERCENT_BAND_PREFIX):
        return f"Unschärfe σ {_sigma_text(name)}"
    return name


def band_description_de(name: str, condition_descriptions: dict[str, str]) -> str:
    if name in condition_descriptions:
        return condition_descriptions[name]
    if name in DESCRIPTIONS_DE:
        return DESCRIPTIONS_DE[name]
    if name in DESCRIPTIONS_DE_TRAILING:
        return DESCRIPTIONS_DE_TRAILING[name]
    if name.startswith("available_cleaned_min_"):
        return _cleaned_description(name)
    if name.startswith(PERCENT_BAND_PREFIX):
        return _blur_description(name)
    return ""


def band_entry(index: int, name: str, condition_descriptions: dict[str, str]) -> dict:
    category, is_total = categorize_layer(name)
    return {
        "index": index,
        "name": name,
        "label_de": band_label_de(name),
        "description_de": band_description_de(name, condition_descriptions),
        "category": category,
        "value_type": band_value_type(name),
        "clipped_to_austria": band_clipped_to_austria(name),
        "is_total": is_total,
        "color_rgba": list(layer_color(name)),
        "default_visible": name in DEFAULT_VISIBLE,
    }


def _crs_text(crs) -> str:
    to_string = getattr(crs, "to_string", None)
    if callable(to_string):
        return to_string()
    return str(crs)


def _pixel_size_m(grid: dict) -> float:
    transform = grid["transform"]
    a = getattr(transform, "a", None)
    e = getattr(transform, "e", None)
    if a is None or e is None:  # z. B. ein einfaches 6-Tupel im Test
        a, e = transform[0], transform[4]
    # Auf 6 Nachkommastellen gerundet: Affine liefert 25.00000000000001,
    # das ist Fließkommarauschen, keine Information.
    return round(float(max(abs(float(a)), abs(float(e)))), 6)


def build_band_manifest(
    raster_path: Path,
    band_names: list[str],
    tags: dict,
    grid: dict,
    condition_descriptions: dict[str, str] | None = None,
) -> dict:
    """Manifest-Objekt zu einem geschriebenen GeoTIFF - ohne Dateizugriff."""
    condition_descriptions = dict(condition_descriptions or {})
    raster_path = Path(raster_path)
    height, width = grid["shape"]
    bounds = [float(v) for v in grid["bounds"]]

    bands = [band_entry(i, name, condition_descriptions) for i, name in enumerate(band_names, 1)]

    caveat = dict(NOE_DKM_CAVEAT)
    caveat["affects"] = {
        "bundesland": "NÖ",
        "bands": [b["index"] for b in bands if _noe_dkm_affected(b["name"])],
    }
    # Schlüsselreihenfolge wie im Contract: id, affects, severity, text_de, ...
    caveat = {
        "id": caveat["id"],
        "affects": caveat["affects"],
        "severity": caveat["severity"],
        "text_de": caveat["text_de"],
        "numbers": dict(caveat["numbers"]),
        "applies_to_other_states": caveat["applies_to_other_states"],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pipeline": str(tags.get("PIPELINE", DEFAULT_PIPELINE)),
        "band_schema": str(tags.get("BAND_SCHEMA", DEFAULT_BAND_SCHEMA)),
        "raster_file": raster_path.name,
        "band_count": len(bands),
        "raster": {
            "crs": _crs_text(grid["crs"]),
            "width": int(width),
            "height": int(height),
            "pixel_size_m": _pixel_size_m(grid),
            "bounds": bounds,
            "dtype": RASTER_DTYPE,
            "nodata": RASTER_NODATA,
            "nodata_meaning": NODATA_MEANING,
        },
        "category_order": list(CATEGORY_ORDER),
        "bands": bands,
        "parameters": dict(tags),
        "sources": {key: dict(value) for key, value in SOURCES.items()},
        "caveats": [caveat],
    }


def manifest_path_for(raster_path: Path) -> Path:
    """<stem>.bands.json neben dem Raster - kein Pfad ist hier fest verdrahtet."""
    raster_path = Path(raster_path)
    return raster_path.with_name(raster_path.stem + MANIFEST_SUFFIX)


def write_band_manifest(
    raster_path: Path,
    band_names: list[str],
    tags: dict,
    grid: dict,
    condition_descriptions: dict[str, str] | None = None,
) -> Path:
    """Schreibt das Band-Manifest neben ``raster_path`` und gibt den Pfad zurück."""
    obj = build_band_manifest(raster_path, band_names, tags, grid, condition_descriptions)
    out_path = manifest_path_for(raster_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path
