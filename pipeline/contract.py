"""Pfadvertrag der Abschichtungskette.

Diese Datei ist die einzige Quelle für Rohpfade, Prep-Ausgaben, Layernamen
und Produktpfade (siehe docs/rewrite/PLAN.md §8, Regel 2: "Der Vertrag wird
gelesen, nicht kopiert"). Nach Welle 0 führt kein Skript mehr einen dieser
Pfade oder Layernamen als Literal - wer einen braucht, importiert ihn von
hier. So ändert eine Umbenennung genau diese Datei statt fünfzehn.

Diese Datei beschreibt nur, sie prüft nicht: kein Dateizugriff beim Import,
keine ``.exists()``-Prüfung, kein ``mkdir``. Sie importiert auch nichts aus
``calc`` oder ``scripts`` - beide importieren umgekehrt von hier, ein
Import in die Gegenrichtung wäre der Zyklus, den dieses Modul gerade
vermeiden soll (siehe pipeline/__init__.py). Wer die Existenz eines Pfads
braucht, prüft selbst - siehe tests/test_contract.py.

Abschnitte: RAW ist der Zielzustand des unveränderlichen Rohbaums (33
Pfade je Domäne). LEGACY_TOT und LEGACY_ENTFAELLT sind zwei verschiedene
Sorten Altlast, die deshalb nicht unter RAW stehen - Unterschied siehe
Kommentar dort. PREP/PREP_FILES sind die Prep-Endprodukte (derived/prep/),
WORK die Zwischenstände der Prep-Stufe (derived/work/), LAYERS die
Checkpoint-Layernamen samt abgeleitetem Pfad, PRODUCTS die Endprodukte.

Regel (CLAUDE.md): RAW (data/) liest nur pipeline/prep/ - alles danach liest
nur PREP/PREP_FILES bzw. LAYERS/PRODUCTS.

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


def _dir_override(env_name: str, default: Path) -> Path:
    """Ausgabeverzeichnis, per Umgebungsvariable umlenkbar (Prüfläufe)."""
    value = os.environ.get(env_name)
    return Path(value).resolve() if value else default


DATA = ROOT / "data"
DERIVED = ROOT / "derived"
DERIVED_PREP = DERIVED / "prep"
# Zwischenstände, Extrakte und Caches der Prep-Stufe (CLAUDE.md: nicht nach
# derived/prep/). Unterverzeichnis je Domäne, siehe WORK unten.
DERIVED_WORK = _dir_override("ABSCHICHTUNG_WORK_DIR", DERIVED / "work")
# Ausgabe der Layer-Stufe und der Finalisierung sind per Umgebungsvariable
# umlenkbar, damit ein Prüflauf (z. B. sha256-Vergleich des End-TIFs) weder
# derived/layers/ noch out/ überschreibt:
#   ABSCHICHTUNG_LAYERS_DIR  -> DERIVED_LAYERS (33+ Checkpoint-TIFs)
#   ABSCHICHTUNG_OUT_DIR     -> OUT (alle Endprodukte aus PRODUCTS)
DERIVED_LAYERS = _dir_override("ABSCHICHTUNG_LAYERS_DIR", DERIVED / "layers")
OUT = _dir_override("ABSCHICHTUNG_OUT_DIR", ROOT / "out")

# run1 - die Vergleichsbasis der alten Kette (osm_wka_distance_zones_widmung_v2_run1.tif,
# sha256 dc58b011…9e3df1). W6.1 hat output/ aus dem Repo herausbewegt, nach
# ~/Documents/master_windkraft/archiv/run1.tif; dort ist die Datei kein
# Rohdatum und kein Produkt (siehe PLAN.md §8), gehört also nicht unter RAW/
# PREP/LAYERS/PRODUCTS oben, sondern - wie ABSCHICHTUNG_ALTREPO in
# tests/test_distance_engine_equivalence.py - nur optional per Umgebungsvariable
# aufgelöst. Vorgabe None: ohne gesetzte Variable ist run1 schlicht nicht da,
# kein Fehler (siehe pipeline/validate.py, tests/test_referenz_tif.py, die
# beide entsprechend überspringen/kurzschließen).
RUN1_TIF = (
    Path(os.environ["ABSCHICHTUNG_RUN1"]).resolve()
    if os.environ.get("ABSCHICHTUNG_RUN1")
    else None
)


# ---------------------------------------------------------------------------
# RAW - die Rohpfade je Domäne (PLAN.md §4 Domänentabelle, §11.2 Zielbaum).
# Endgültig: W0.1 hat den data/-Baum bereits in diese Form gebracht, hier
# ändert sich nichts mehr. Jeder Eintrag ist mit einer Codestelle belegt
# (siehe Bericht zu W0.2); Verzeichnis statt Einzeldatei genau dort, wo der
# Code selbst per glob/Namenskonstruktion in ein Verzeichnis greift.
# ---------------------------------------------------------------------------

RAW = {
    "admin": {
        # calc/abschichtung_common.py:624 (cfg["paths"]["vgd"]);
        # ebenso von pipeline/prep/kataster/diagnostics.py (Paket W1.P2 hat
        # scripts/preprocessing/create_noe_dkm_polygon_fill_map.py dorthin
        # verschoben) und scripts/noe/extract_noe_vector_layers.py gelesen.
        "vgd": DATA / "admin" / "VGD_Oesterreich_gen_50_20221002" / "VGD_50_generalisiert.shp",
    },
    "kataster": {
        # pipeline/prep/kataster/diagnostics.py:SYMBOL_CSV,
        # pipeline/prep/kataster/a_noe_polygonize.py, b_export_parquet.py
        # (Paket W1.P2 hat scripts/preprocessing/{create_noe_dkm_polygon_fill_map,
        # export_at_dkm_geoparquet}.py hierher verschoben und aufgeteilt).
        "symbol_csv": DATA / "kataster" / "BEV_DKM_DXF_Symbole_V2.6.csv",
        # pipeline/prep/kataster/diagnostics.py:ZIP_PATH,
        # pipeline/prep/kataster/a_noe_polygonize.py (Stufe a - siehe oben).
        "noe_dxf_zip": DATA / "kataster" / "KAT_DKM_Niederoesterreich_DXF_20230401.zip",
        # Die übrigen acht Bundesländer: pipeline/prep/kataster/common.py
        # (DEFAULT_SHP_ARCHIVES, je über ArchiveSpec.raw_key aufgelöst),
        # gelesen von b_export_parquet.py (Stufe b).
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
        # calc/bev_register.py: nimmt ein Verzeichnis entgegen und
        # sucht darin selbst per glob nach dem jüngsten Stichtags-ZIP bzw.
        # nach ADRESSE.csv/GEBAEUDE.csv als Klartext-Fallback. Aufrufer:
        # scripts/widmung_v2/02_build_hig_sources.py:198 (--address-dir) -
        # seit W6.1 aus dem Repo entfernt, letzter Stand im Commit f1d00f7 -,
        # calc/streusiedlung.py:104-105.
        "address_dir": DATA / "adressen",
    },
    "widmung": {
        # calc/widmung_sources.py: DATASETS[*]/_read_raw(); WIDMUNG
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
        # scripts/widmung_v2/04_create_distance_zones.py:378 (--osm-pbf) -
        # beide seit W6.1 aus dem Repo entfernt, letzter Stand je im Commit
        # f1d00f7.
        "pbf": DATA / "osm" / "austria-260330.osm.pbf",
        # powerlines_gpkg steht NICHT hier: Paket W1.2 hat data/osm_power_lines.gpkg
        # gelöscht und den zugehörigen LEGACY_ENTFAELLT-Eintrag ausgetragen
        # (siehe dort) - der einzige Codeleser, abschichtung_common.py:966,
        # war ohnehin nur ein Fallback, der nie griff, solange das PBF
        # vorhanden ist.
    },
    "windkraft": {
        # Geliefertes Bestandsverzeichnis. Das GeoJSON folgt RFC 7946
        # und trägt deshalb kein crs-Member; pipeline/prep/windkraft.py weist
        # beim Lesen explizit CRS84/EPSG:4326 zu und schreibt EPSG:31287.
        # Es ist die einzige positive Quelle für Bestands-WKA. OSM-Windpower
        # bleibt ausschließlich ein Negativfilter für Gebäude.
        "standorte": DATA / "windkraft" / "windkraft_standorte_at.geojson",
    },
    "gelaende": {
        # calc/abschichtung_common.py:1256, :307 (Fallback)
        "dgm": DATA / "gelaende" / "DGM_R25.tif",
        # calc/abschichtung_common.py:1282, :307 (Fallback)
        "wind_pd_150": DATA / "gelaende" / "AUT_power-density_150m.tif",
    },
    "natur": {
        # calc/abschichtung_common.py:1164 (cfg["paths"]["nsg_zip"]).
        # nsg_gpkg (Mitgliedsname im ZIP) und nsg_layers (Layernamen im GPKG)
        # sind keine Pfade - die bleiben Nicht-Pfad-Parameter in config.json.
        "nsg_zip": DATA / "natur" / "SG_AT_2024_v_April_Stand_3_April_2024.zip",
    },
    "zonen": {
        # scripts/widmung_v2/04_create_distance_zones.py:365 (--official-zoning-geojson)
        "official_zoning_noe": DATA / "zonen" / "zonierung_noe.json",
        # Verzeichnis: enthält Sbg.shp/Stmk.shp, von calc/wind_zones.py
        # per <zone_dir>/<key>.shp aufgelöst (kein eigener source_path);
        # scripts/widmung_v2/04_create_distance_zones.py:370 (--vorrangzonen-dir).
        "luca_zonen_dir": DATA / "zonen" / "luca_zonen",
        # calc/wind_zones.py:100,126 (hartkodierter source_path,
        # Positiv- UND Ausschlusszonen im selben Layer, per Attributfilter getrennt).
        "eignungszonen_zip": DATA / "zonen" / "WK_Eignungszonen.zip",
        # calc/wind_zones.py:115 (hartkodierter source_path).
        "red3_zip": DATA / "zonen" / "RED_III_Windkraftbeschleunigungszone.zip",
        # ausschlusszone_zip steht NICHT (mehr) hier: Paket W1.7 hat die
        # Registrierung in calc/wind_zones.py entfernt (Entscheidung
        # (a) des Plans), es gibt also keinen Codeleser mehr - der Eintrag ist
        # mit dem Codeleser aus LEGACY_ENTFAELLT entfallen, nicht erst mit der
        # Datei. Paket W1.2 hat die Datei selbst (data/WINDKRAFT_AUSSCHLUSSZONE.zip)
        # inzwischen ebenfalls gelöscht.
    },
    "noe_sekrop": {
        # pipeline/prep/noe_sekrop.py (PDF_PATH, beide Stufen) - vormals
        # scripts/noe/extract_noe_vector_layers.py:48 und
        # scripts/noe/align_pdf_shapefile.py, per Paket W1.P9 dorthin
        # verschoben (siehe dessen Bericht). calc/noe/pdf_align.py:45
        # bleibt als geteilte GPTS-Konstante bestehen, von dort importiert.
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
# sie sonst nicht mehr auflösen könnte (siehe calc/config.py).
#
# LEGACY_ENTFAELLT - Pfade, die existieren und heute tatsächlich gelesen
# werden (bis zu ihrer Entfernung gilt für sie also dieselbe Zusicherung
# wie für RAW: siehe tests/test_contract.py), deren Quelle aber in Welle 1
# entfällt. Je Eintrag steht, welches Paket sie entfernt.
# ---------------------------------------------------------------------------

LEGACY_TOT: dict[str, Path] = {
    # Leer: "osm_dir" (nie existiertes Shapefile) und "wind_pd_100" (kein
    # Konsument) sind mit der prep-Grenze (CLAUDE.md) aus calc/config.py und
    # dem Legacy-Fallback in calc/abschichtung_common.py entfallen.
}

LEGACY_ENTFAELLT: dict[str, Path] = {
    # War: "powerlines_gpkg" -> DATA / "osm_power_lines.gpkg". Paket W1.2 hat
    # die Datei gelöscht (kein Codeleser, siehe RAW["osm"]-Kommentar oben)
    # und diesen Eintrag ausgetragen - siehe Bericht zu W1.2. Aktuell leer;
    # bleibt als Register für künftige Welle-1-Funde stehen (§13.1).
}


# ---------------------------------------------------------------------------
# PREP / WORK - Ausgaben der Prep-Stufe je Domäne (CLAUDE.md: Stufentrennung
# und einheitliches Format).
#
# derived/prep/<domäne>/ enthält ausschließlich die Endprodukte, die die
# nächste Stufe liest (und die man zum Weitergeben ohne Rohdaten mitschickt):
#   Vektor -> GeoParquet, EPSG:31287 (mit Geo-Metadaten)
#   Raster -> GeoTIFF exakt auf dem Zielraster (EPSG:31287, 25 m, 24001x14001)
# daneben je Domäne höchstens Berichte (*.md, *.json inkl. .fingerprint.json).
# Zwischenstände, Extrakte und Caches liegen in derived/work/<domäne>/.
#
# PREP und WORK sind flach: ein Verzeichnis je Domäne (keine a_/b_-Stufen
# mehr in PREP). Die Dateien der Endprodukte stehen in PREP_FILES.
# ---------------------------------------------------------------------------

PREP_DOMAINS = (
    "admin", "kataster", "adressen", "widmung", "osm",
    "windkraft", "gelaende", "natur", "zonen", "noe_sekrop",
)

PREP = {domain: DERIVED_PREP / domain for domain in PREP_DOMAINS}
WORK = {domain: DERIVED_WORK / domain for domain in PREP_DOMAINS}

# Die Dateien in PREP[domain], die nachfolgende Stufen lesen. Wer einen
# Dateinamen braucht, holt ihn hier - nicht aus einem prep-Modul.
_OSM_LAYER_KEYS = (
    "buildings", "windpower", "aerialways", "powerlines",
    "roads", "railways", "military", "transport", "nature", "water",
)
_ZONEN_KEYS = ("Stmk", "Sbg", "Bgld", "RED3", "NOE")
_WIDMUNG_BUCKETS = ("wohn_misch", "haeuser_im_gruenen", "industrie_negativ")
_NOE_SEKROP_LAYERS = ("pdf_750m_geb", "pdf_750m_gwr", "pdf_750m_gruenland_widmung")

PREP_FILES: dict[str, dict[str, Path]] = {
    "admin": {
        "gemeinden": PREP["admin"] / "gemeinden.parquet",
        "bundesland_masken": PREP["admin"] / "bundesland_masken.parquet",
    },
    "kataster": {
        # Große DKM-Datei (nur noch pipeline/analyse_raster.py liest sie; wird
        # NICHT weitergegeben). Alles andere nach prep liest die kleinen
        # Streusiedlungs-Produkte (Stufe c, pipeline/prep/kataster/c_streusiedlung.py).
        "at_dkm_gst_nfl": PREP["kataster"] / "at_dkm_gst_nfl_epsg31287.geoparquet",
        "streusiedlung_kandidaten": PREP["kataster"] / "streusiedlung_kandidaten.parquet",
        "streusiedlung_garten": PREP["kataster"] / "streusiedlung_garten.parquet",
    },
    "adressen": {
        "adressen": PREP["adressen"] / "adressen_31287.parquet",
        "gebaeude": PREP["adressen"] / "bev_gebaeude_31287.parquet",
    },
    "widmung": {b: PREP["widmung"] / f"{b}_combined.parquet" for b in _WIDMUNG_BUCKETS},
    "osm": {k: PREP["osm"] / f"{k}.parquet" for k in _OSM_LAYER_KEYS},
    "windkraft": {"standorte": PREP["windkraft"] / "standorte.parquet"},
    "gelaende": {
        "dgm": PREP["gelaende"] / "dgm.tif",
        "wind_pd_150": PREP["gelaende"] / "wind_pd_150.tif",
    },
    "natur": {"schutzgebiete": PREP["natur"] / "schutzgebiete.parquet"},
    "zonen": {k: PREP["zonen"] / f"{k}.parquet" for k in _ZONEN_KEYS},
    "noe_sekrop": {n: PREP["noe_sekrop"] / f"{n}.parquet" for n in _NOE_SEKROP_LAYERS},
}

# Zulässige Endungen in derived/prep/ (tests/test_prep_grenze.py).
PREP_PRODUCT_SUFFIXES = (".parquet", ".geoparquet", ".tif")
PREP_REPORT_SUFFIXES = (".md", ".json")

# Zu den Produkten gehörende Berichte (Zählwerte, Parameter) - kein eigenes Produkt.
PREP_REPORT_FILES = {
    "kataster": {
        "streusiedlung_bericht": PREP["kataster"] / "streusiedlung_bericht.json",
    },
}


# ---------------------------------------------------------------------------
# LAYERS - Checkpoint-Layer der Rasterisierungsstufe. Bezeichner zuerst, Pfad
# wird daraus abgeleitet (<name>.tif unter derived/layers/) - wie es heute schon
# layer_path() in calc/abschichtung_common.py tut. Namensherkunft (Stand W0.2,
# historisch): die 33 Checkpoints lagen damals noch unter
# output/abschichtung_widmung_v2/distance_layers/, Datei- und Codenamen waren
# dort bereits deckungsgleich (siehe Bericht zu W0.2) - dieses output/ existiert
# seit W6.1 nicht mehr im Repo (siehe pipeline/validate.py). Ausnahme: der
# Checkpoint noe_pdf_hig_source wurde dort nie gelesen (Paket W1.6 hat den
# Erzeuger entfernt) und fehlt deshalb hier absichtlich.
# ---------------------------------------------------------------------------

LAYER_NAMES = (
    # scripts/widmung_v2/02_build_hig_sources.py:SOURCE_LAYER_NAMES - seit
    # W6.1 aus dem Repo entfernt, letzter Stand im Commit f1d00f7 - git show
    # f1d00f7:scripts/widmung_v2/02_build_hig_sources.py.
    "official_settlement_source",
    "ferienhaus_tourismus_source",
    "official_hig_source",
    "noe_pdf_750m_zones",
    "hig_hulls_source",
    "bewohnt_einzellage_source",
    "nonresidential_hulls_source",
    # scripts/widmung_v2/03_build_osm_layers.py:OSM_LAYER_NAMES,
    # INFRA_LAYER_NAMES, AIRPORT_LAYER_NAMES - seit W6.1 aus dem Repo
    # entfernt, letzter Stand im Commit f1d00f7 - git show
    # f1d00f7:scripts/widmung_v2/03_build_osm_layers.py.
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
    # W7.1 (docs/rewrite/PLAN.md, Neuzuschnitt "Layer-Struktur v4"):
    # angehängt an Index 39-44, laut schnittstelle-manifest-2.2.md §2 -
    # verbindlich für Produzent UND Dashboard (Paket W7.3). Kein Index 1-38
    # oben verschiebt sich; die Bänder selbst entstehen in
    # pipeline/layers/geo.py (39, 42-44) bzw. pipeline/layers/osm.py (40, 41)
    # als Checkpoint einer früheren Build-Gruppe - Baureihenfolge dort weicht
    # bewusst von dieser Bandreihenfolge ab (siehe dortige Kommentare).
    "haeuser_im_gruenen_source",
    "general_buildings_roh_osm",
    "general_buildings_roh_dkm",
    "sources_human",
    "sources_nature",
    "sources_geography",
    # 30.09.2026: Freileitungen >= 110 kV wieder als Ausschlusskriterium,
    # angehaengt an Index 45 (kein Index 1-44 verschiebt sich). Erzeuger:
    # pipeline/layers/osm.py (INFRA_LAYER_NAMES).
    "power_lines_110kv_plus",
)

LAYERS = {name: DERIVED_LAYERS / f"{name}.tif" for name in LAYER_NAMES}


# ---------------------------------------------------------------------------
# PRODUCTS - ursprünglich die vier Endprodukte aus PLAN.md §3; seit W7.1
# (Neuzuschnitt, schnittstelle-manifest-2.2.md §3) sechs: der Punkte-Export
# des WKA-Bestands und LAYER.md kommen dazu. Beide Erzeuger liegen bei
# Bahn 3 (neu pipeline/export/wka_bestand.py, pipeline/export/layer_doc.py -
# nicht Teil dieser Datei/dieses Pakets), die Pfadeinträge selbst trägt
# Bahn 1 ein, weil pipeline/contract.py als Ganzes hier liegt.
# ---------------------------------------------------------------------------

PRODUCTS = {
    "abschichtung_tif": OUT / "abschichtung.tif",
    "abschichtung_bands_json": OUT / "abschichtung.bands.json",
    "dashboard_dir": OUT / "dashboard",
    "gemeinden_geojson": OUT / "gemeinden.geojson",
    "wka_bestand_punkte_geojson": OUT / "wka_bestand_punkte.geojson",
    "layer_md": OUT / "LAYER.md",
    # W7.6: siebtes Endprodukt - der Vertrag, WIE abschichtung.bands.json zu
    # lesen ist (docs/LAYER-MANIFEST.md), gelesen nicht kopiert bis hierher,
    # ab W7.6 auch nach out/ übergeben (make/export/layer_manifest_md.mk).
    "layer_manifest_md": OUT / "LAYER-MANIFEST.md",
    # Zweites Produkt, nur Analyse (nicht Teil des Konsumentenvertrags,
    # von Viewer/Dashboard/Export nicht gelesen): Kataster-Nutzungsklassen auf
    # exakt dem Raster von abschichtung.tif (pipeline/analyse_raster.py).
    "abschichtung_analyse_tif": OUT / "abschichtung_analyse.tif",
    "abschichtung_analyse_bands_json": OUT / "abschichtung_analyse.bands.json",
}

# Fingerabdruck-Ablage der Stufe analyse-raster (Skip-if-unchanged).
# Folgt OUT, wenn ABSCHICHTUNG_OUT_DIR gesetzt ist (Prüflauf schreibt nicht
# nach derived/).
DERIVED_ANALYSE_RASTER = (
    OUT / ".analyse_raster" if os.environ.get("ABSCHICHTUNG_OUT_DIR") else DERIVED / "analyse_raster"
)
