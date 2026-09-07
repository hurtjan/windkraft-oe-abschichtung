"""Pfadvertrag der Abschichtungskette.

Diese Datei ist die einzige Quelle für Rohpfade, Prep-Ausgaben, Layernamen
und Produktpfade (siehe docs/rewrite/PLAN.md §8, Regel 2: "Der Vertrag wird
gelesen, nicht kopiert"). Nach Welle 0 führt kein Skript mehr einen dieser
Pfade oder Layernamen als Literal - wer einen braucht, importiert ihn von
hier. So ändert eine Umbenennung genau diese Datei statt fünfzehn.

Diese Datei beschreibt nur, sie prüft nicht: kein Dateizugriff beim Import,
keine ``.exists()``-Prüfung, kein ``mkdir``. Sie importiert auch nichts aus
``windkraft`` oder ``scripts`` - beide importieren umgekehrt von hier, ein
Import in die Gegenrichtung wäre der Zyklus, den dieses Modul gerade
vermeiden soll (siehe pipeline/__init__.py). Wer die Existenz eines Pfads
braucht, prüft selbst - siehe tests/test_contract.py.

Abschnitte: RAW ist der Zielzustand des unveränderlichen Rohbaums (33
Pfade je Domäne). LEGACY_TOT und LEGACY_ENTFAELLT sind zwei verschiedene
Sorten Altlast, die deshalb nicht unter RAW stehen - Unterschied siehe
Kommentar dort. PREP sind die Prep-Ausgaben, LAYERS die 33
Checkpoint-Layernamen samt abgeleitetem Pfad, PRODUCTS die vier
Endprodukte.

Verwendung, zum Beispiel:
    from pipeline import contract
    vgd_path = contract.RAW["admin"]["vgd"]
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Wurzel
# ---------------------------------------------------------------------------

# Überschreibbar per Umgebungsvariable, damit ein Test oder ein paralleles
# Worktree mit einer anderen Ablage arbeiten kann, ohne diese Datei zu ändern.
ROOT = Path(
    os.environ.get("ABSCHICHTUNG_ROOT", str(Path(__file__).resolve().parents[1]))
).resolve()

DATA = ROOT / "data"
BUILD = ROOT / "build"
BUILD_PREP = BUILD / "prep"
BUILD_LAYERS = BUILD / "layers"
OUT = ROOT / "out"


# ---------------------------------------------------------------------------
# RAW - die Rohpfade je Domäne (PLAN.md §4 Domänentabelle, §11.2 Zielbaum).
# Endgültig: W0.1 hat den data/-Baum bereits in diese Form gebracht, hier
# ändert sich nichts mehr. Jeder Eintrag ist mit einer Codestelle belegt
# (siehe Bericht zu W0.2); Verzeichnis statt Einzeldatei genau dort, wo der
# Code selbst per glob/Namenskonstruktion in ein Verzeichnis greift.
# ---------------------------------------------------------------------------

RAW = {
    "admin": {
        # windkraft/calc/abschichtung_common.py:624 (cfg["paths"]["vgd"]);
        # ebenso von scripts/preprocessing/create_noe_dkm_polygon_fill_map.py
        # und scripts/noe/extract_noe_vector_layers.py gelesen.
        "vgd": DATA / "admin" / "VGD_Oesterreich_gen_50_20221002" / "VGD_50_generalisiert.shp",
    },
    "kataster": {
        # scripts/preprocessing/create_noe_dkm_polygon_fill_map.py:51,
        # scripts/preprocessing/export_at_dkm_geoparquet.py:68
        "symbol_csv": DATA / "kataster" / "BEV_DKM_DXF_Symbole_V2.6.csv",
        # scripts/preprocessing/create_noe_dkm_polygon_fill_map.py:50,
        # scripts/preprocessing/export_at_dkm_geoparquet.py:69
        "noe_dxf_zip": DATA / "kataster" / "KAT_DKM_Niederoesterreich_DXF_20230401.zip",
        # Die übrigen acht Bundesländer: scripts/preprocessing/
        # export_at_dkm_geoparquet.py:104-113 (DEFAULT_SHP_ARCHIVES), unter
        # --data-dir (Default ROOT/"data/kataster") gejoint.
        "burgenland_zip": DATA / "kataster" / "KAT_DKM_Burgenland_SHP_20210401.zip",
        "kaernten_zip": DATA / "kataster" / "KAT_DKM_Kaernten_SHP_20221001.zip",
        "oberoesterreich_zip": DATA / "kataster" / "KAT_DKM_Oberoesterreich_SHP_20221001.zip",
        "salzburg_zip": DATA / "kataster" / "KAT_DKM_Salzburg_SHP_20221001.zip",
        "steiermark_zip": DATA / "kataster" / "KAT_DKM_Steiermark_SHP_20221001.zip",
        "tirol_zip": DATA / "kataster" / "KAT_DKM_Tirol_SHP_20221001.zip",
        "vorarlberg_zip": DATA / "kataster" / "KAT_DKM_Vorarlberg_SHP_20221001.zip",
        "wien_zip": DATA / "kataster" / "KAT_DKM_Wien_SHP_20221001.zip",
    },
    "adressen": {
        # windkraft/calc/bev_register.py: nimmt ein Verzeichnis entgegen und
        # sucht darin selbst per glob nach dem jüngsten Stichtags-ZIP bzw.
        # nach ADRESSE.csv/GEBAEUDE.csv als Klartext-Fallback. Aufrufer:
        # scripts/widmung_v2/02_build_hig_sources.py:198 (--address-dir),
        # windkraft/calc/streusiedlung.py:104-105.
        "address_dir": DATA / "adressen",
    },
    "widmung": {
        # windkraft/calc/widmung_sources.py: DATASETS[*]/_read_raw(); WIDMUNG
        # = ROOT/"data"/"widmung" (dort zusammengesetzt, nicht als Literal
        # sichtbar - siehe PLAN.md §11.1).
        "burgenland": DATA / "widmung" / "burgenland" / "WIDMUNGSFLAECHEN.zip",
        "kaernten": DATA / "widmung" / "kaernten" / "flawi_ktn_gpkg.zip",
        "niederoesterreich": DATA / "widmung" / "niederoesterreich" / "RRU_WI_HUELLE.gpkg",
        "oberoesterreich": DATA / "widmung" / "oberoesterreich" / "FLWI_WIDMUNGEN_F.zip",
        "salzburg": DATA / "widmung" / "salzburg" / "Flaechenwidmung_Shapefile.zip",
        "steiermark_bauland": DATA / "widmung" / "steiermark" / "Bauland.zip",
        "steiermark_flaewi": DATA / "widmung" / "steiermark" / "Flaewi.shp.zip",
        # Verzeichnis: der Dateiname trägt eine Stichtags-ID
        # (FLW_Flaechenwidmung_<id>.gpkg) und wird per glob aufgelöst
        # (widmung_sources.py:_tirol_gpkg).
        "tirol_dir": DATA / "widmung" / "tirol",
        "vorarlberg": DATA / "widmung" / "vorarlberg" / "fwp_flaeche.gpkg",
        "wien": DATA / "widmung" / "wien" / "genflwidmung_wien.geojson",
    },
    "osm": {
        # scripts/widmung_v2/03_build_osm_layers.py:231,
        # scripts/widmung_v2/04_create_distance_zones.py:378 (--osm-pbf)
        "pbf": DATA / "osm" / "austria-260330.osm.pbf",
        # powerlines_gpkg steht NICHT hier: Paket W1.2 hat data/osm_power_lines.gpkg
        # gelöscht und den zugehörigen LEGACY_ENTFAELLT-Eintrag ausgetragen
        # (siehe dort) - der einzige Codeleser, abschichtung_common.py:966,
        # war ohnehin nur ein Fallback, der nie griff, solange das PBF
        # vorhanden ist.
    },
    "gelaende": {
        # windkraft/calc/abschichtung_common.py:1256, :307 (Fallback)
        "dgm": DATA / "gelaende" / "DGM_R25.tif",
        # windkraft/calc/abschichtung_common.py:1282, :307 (Fallback)
        "wind_pd_150": DATA / "gelaende" / "AUT_power-density_150m.tif",
    },
    "natur": {
        # windkraft/calc/abschichtung_common.py:1164 (cfg["paths"]["nsg_zip"]).
        # nsg_gpkg (Mitgliedsname im ZIP) und nsg_layers (Layernamen im GPKG)
        # sind keine Pfade - die bleiben Nicht-Pfad-Parameter in config.json.
        "nsg_zip": DATA / "natur" / "SG_AT_2024_v_April_Stand_3_April_2024.zip",
    },
    "zonen": {
        # scripts/widmung_v2/04_create_distance_zones.py:365 (--official-zoning-geojson)
        "official_zoning_noe": DATA / "zonen" / "zonierung_noe.json",
        # Verzeichnis: enthält Sbg.shp/Stmk.shp, von windkraft/calc/wind_zones.py
        # per <zone_dir>/<key>.shp aufgelöst (kein eigener source_path);
        # scripts/widmung_v2/04_create_distance_zones.py:370 (--vorrangzonen-dir).
        "luca_zonen_dir": DATA / "zonen" / "luca_zonen",
        # windkraft/calc/wind_zones.py:100,126 (hartkodierter source_path,
        # Positiv- UND Ausschlusszonen im selben Layer, per Attributfilter getrennt).
        "eignungszonen_zip": DATA / "zonen" / "WK_Eignungszonen.zip",
        # windkraft/calc/wind_zones.py:115 (hartkodierter source_path).
        "red3_zip": DATA / "zonen" / "RED_III_Windkraftbeschleunigungszone.zip",
        # ausschlusszone_zip steht NICHT (mehr) hier: Paket W1.7 hat die
        # Registrierung in windkraft/calc/wind_zones.py entfernt (Entscheidung
        # (a) des Plans), es gibt also keinen Codeleser mehr - der Eintrag ist
        # mit dem Codeleser aus LEGACY_ENTFAELLT entfallen, nicht erst mit der
        # Datei. Paket W1.2 hat die Datei selbst (data/WINDKRAFT_AUSSCHLUSSZONE.zip)
        # inzwischen ebenfalls gelöscht.
    },
    "noe_sekrop": {
        # scripts/noe/extract_noe_vector_layers.py:48,
        # windkraft/noe/pdf_align.py:45, scripts/noe/align_pdf_shapefile.py
        # (DATA / "noe_sekrop" / ... - zusammengesetzt, siehe PLAN.md §11.1)
        "pdf": DATA / "noe_sekrop" / "TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf",
    },
}


# ---------------------------------------------------------------------------
# LEGACY_TOT / LEGACY_ENTFAELLT - zwei verschiedene Sorten Altlast, die
# beide NICHT unter RAW stehen. RAW beschreibt den Zielzustand des
# unveränderlichen Rohbaums; ein Welle-1-Paket, das RAW["osm"] oder
# RAW["zonen"] durchgeht, soll dort keine Datei finden, die es selbst
# gerade löscht. Die beiden Sektionen unterscheiden sich darin, WAS an
# ihnen unwahr ist:
#
# LEGACY_TOT - Pfade, die nie existiert haben. config.json bzw. der Code
# deklariert sie seit jeher, aber der Codezweig, der sie läse, ist
# unerreichbar (PLAN.md §11.1, Klasse "U": deklariert, kein Konsument).
# Kein Rohdatum, nichts, das je verschwinden könnte. W1.x entfernt beide
# Einträge ersatzlos; bis dahin müssen sie hier stehen, weil config.json
# sie sonst nicht mehr auflösen könnte (siehe windkraft/config.py).
#
# LEGACY_ENTFAELLT - Pfade, die existieren und heute tatsächlich gelesen
# werden (bis zu ihrer Entfernung gilt für sie also dieselbe Zusicherung
# wie für RAW: siehe tests/test_contract.py), deren Quelle aber in Welle 1
# entfällt. Je Eintrag steht, welches Paket sie entfernt.
# ---------------------------------------------------------------------------

LEGACY_TOT = {
    # config.json:osm_dir - zeigt auf ein nie existiertes Shapefile
    # ("austria-260328-free.shp"); die tatsächliche OSM-Quelle ist
    # RAW["osm"]["pbf"] ("austria-260330.osm.pbf" - anderer Stichtag,
    # anderes Format).
    "osm_dir": DATA / "osm" / "austria-260328-free.shp",
    # config.json:wind_pd_100 - deklariert, kein Konsument, Datei existiert
    # nicht. RAW["gelaende"]["wind_pd_150"] ist die tatsächlich gelesene
    # Leistungsdichtehöhe.
    "wind_pd_100": DATA / "gelaende" / "AUT_power-density_100m.tif",
}

LEGACY_ENTFAELLT: dict[str, Path] = {
    # War: "powerlines_gpkg" -> DATA / "osm_power_lines.gpkg". Paket W1.2 hat
    # die Datei gelöscht (kein Codeleser, siehe RAW["osm"]-Kommentar oben)
    # und diesen Eintrag ausgetragen - siehe Bericht zu W1.2. Aktuell leer;
    # bleibt als Register für künftige Welle-1-Funde stehen (§13.1).
}


# ---------------------------------------------------------------------------
# PREP - Ausgaben der Prep-Stufe(n) je Domäne (PLAN.md §4, Spalte "Prep").
# Zielzustand: existiert nach W0.2 noch nicht, die Prep-Pakete legen die
# Verzeichnisse tatsächlich an und schreiben hinein. "gelaende" hat keine
# Prep-Stufe (Raster liegen schon im Zielgitter, siehe PLAN.md §4) und taucht
# hier deshalb nicht auf.
# ---------------------------------------------------------------------------

PREP = {
    "admin": BUILD_PREP / "admin",
    # Kataster: zwei Stufen, weil die NÖ-Polygonisierung teuer ist und vom
    # billigeren Parquet-Export getrennt bleibt (PLAN.md §4/§3).
    "kataster": {
        "a_noe_polygonize": BUILD_PREP / "kataster" / "a_noe_polygonize",
        "b_export_parquet": BUILD_PREP / "kataster" / "b_export_parquet",
    },
    "adressen": BUILD_PREP / "adressen",
    "widmung": BUILD_PREP / "widmung",
    # OSM: zwei Stufen, weil die osmium-Extraktion teuer ist und die
    # Layer-Ableitung oft wiederholt wird (PLAN.md §4).
    "osm": {
        "a_extract": BUILD_PREP / "osm" / "a_extract",
        "b_layers": BUILD_PREP / "osm" / "b_layers",
    },
    "natur": BUILD_PREP / "natur",
    "zonen": BUILD_PREP / "zonen",
    # NÖ SekROP: zwei Stufen, Karten-Alignment vor Vektorisierung (PLAN.md §4).
    "noe_sekrop": {
        "a_align": BUILD_PREP / "noe_sekrop" / "a_align",
        "b_vectorize": BUILD_PREP / "noe_sekrop" / "b_vectorize",
    },
}


# ---------------------------------------------------------------------------
# LAYERS - Checkpoint-Layer der Rasterisierungsstufe. Bezeichner zuerst, Pfad
# wird daraus abgeleitet (<name>.tif unter build/layers/) - wie es heute schon
# layer_path() in windkraft/calc/abschichtung_common.py tut. Zielzustand:
# heute liegen die entsprechenden 33 Checkpoints noch unter
# output/abschichtung_widmung_v2/distance_layers/, Datei- und Codenamen sind
# dort bereits deckungsgleich (siehe Bericht zu W0.2). Ausnahme: der Checkpoint
# noe_pdf_hig_source wurde dort nie gelesen (Paket W1.6 hat den Erzeuger
# entfernt) und fehlt deshalb hier absichtlich.
# ---------------------------------------------------------------------------

LAYER_NAMES = (
    # scripts/widmung_v2/02_build_hig_sources.py:SOURCE_LAYER_NAMES
    "official_settlement_source",
    "ferienhaus_tourismus_source",
    "official_hig_source",
    "noe_pdf_750m_zones",
    "hig_hulls_source",
    "bewohnt_einzellage_source",
    "nonresidential_hulls_source",
    # scripts/widmung_v2/03_build_osm_layers.py:OSM_LAYER_NAMES,
    # INFRA_LAYER_NAMES, AIRPORT_LAYER_NAMES
    "cableway_buildings_source",
    "general_buildings_source",
    "road_motorway_trunk",
    "road_federal_state",
    "rail_main",
    "cableway_people_150m",
    "military_restricted_area",
    "airport_area_major",
    "airport_runway_corridor_5km",
    # scripts/widmung_v2/04_create_distance_zones.py: HIG_FAMILY_SOURCE_BANDS,
    # BUFFER_BANDS, NATURE_BANDS, GEOGRAPHY_BANDS, WATER_BANDS,
    # OFFICIAL_ZONING_BANDS, WKA_BESTAND_BAND
    "haeuser_im_gruenen_ferienhaus",
    "haeuser_im_gruenen_widmung",
    "haeuser_im_gruenen_streusiedlung",
    "haeuser_im_gruenen_noe_pdf",
    "settlement_buffer",
    "haeuser_im_gruenen",
    "nonresidential_hulls_buffer",
    "cableway_buildings_buffer",
    "general_buildings_buffer",
    "nature_protection_areas",
    "osm_nature_protection_areas",
    "geography_slope_too_steep",
    "geography_elevation_too_high",
    "geography_wind_too_low",
    "geography_water_bodies",
    "official_wind_zoning",
    "wka_bestand_ausserhalb_zonen",
)

LAYERS = {name: BUILD_LAYERS / f"{name}.tif" for name in LAYER_NAMES}


# ---------------------------------------------------------------------------
# PRODUCTS - genau die vier Endprodukte aus PLAN.md §3. Zielzustand.
# ---------------------------------------------------------------------------

PRODUCTS = {
    "abschichtung_tif": OUT / "abschichtung.tif",
    "abschichtung_bands_json": OUT / "abschichtung.bands.json",
    "dashboard_dir": OUT / "dashboard",
    "gemeinden_geojson": OUT / "gemeinden.geojson",
}
