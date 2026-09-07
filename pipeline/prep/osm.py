"""Prep: OSM, zwei Stufen (Paket W1.P5, docs/rewrite/PLAN.md §7, §4).

Liest die OSM-Rohquelle (``contract.RAW["osm"]["pbf"]`` -
``austria-260330.osm.pbf``, 760 MB laut PLAN.md §4) und schreibt zwei
Ableitungen nach ``contract.PREP["osm"]``:

- ``a_extract`` - die teure Hälfte: für jede der zehn tatsächlich
  gelesenen Objektgruppen ein ``osmium tags-filter`` (Rohquelle ->
  gefiltertes ``.osm.pbf``) gefolgt von einem ``osmium export``
  (gefiltertes ``.osm.pbf`` -> ``.geojsonseq``). Genau die zwei
  Unterprozessaufrufe, die ``windkraft/calc/abschichtung_common.py:
  osm_layer_path()`` heute bei jedem Kettenlauf pro Objektgruppe absetzt
  (Zeile ~504/509), hier einmalig für die GANZE Landesfläche statt für
  einen bbox-Ausschnitt.
- ``b_layers`` - die billige, "oft wiederholte" Hälfte: liest jede
  ``.geojsonseq``-Datei aus ``a_extract`` mit GeoPandas, leitet
  ``fclass``/``type`` genau wie ``read_layer()`` (Zeile ~517-546) ab und
  reprojiziert nach EPSG:31287. Ergebnis: eine GeoParquet-Datei je
  Objektgruppe.

## Welche zehn Objektgruppen - und warum nicht dreizehn

``OSM_PBF_FILTERS``/``OSM_PBF_INCLUDE_TAGS`` in ``abschichtung_common.py``
deklarieren dreizehn Schlüssel. Ein Repo-weiter Suchlauf über alle
Aufrufstellen von ``osm_layer_path(cfg, ..., "<key>", ...)`` (in
``scripts/widmung_v2/03_build_osm_layers.py`` und
``scripts/widmung_v2/04_create_distance_zones.py``) zeigt: nur ZEHN davon
werden von irgendeinem Konsumenten tatsächlich gelesen -

    buildings   OSM-Gebäude (Way/Relation `building=*`)
    windpower   Windkraftanlagen (Node/Way/Relation, WIND_POWER_OSM_FILTERS)
    aerialways  Seilbahnen/Lifte (alle Typen, ungefiltert)
    powerlines  Stromleitungen (`power=line`/`minor_line`)
    roads       Straßen (`highway=*`)
    railways    Bahnstrecken (`railway=*`)
    military    Militärflächen (`landuse=military` bzw. `military=*`)
    transport   Flugverkehr (`aeroway=*`)
    nature      Schutzgebiets-Tags (`boundary=protected_area/national_park`,
                `leisure=nature_reserve`, `protect_class`, `protection_title`)
    water       Gewässer (`natural=water`, `waterway=riverbank`,
                `landuse=reservoir`)

Die übrigen drei (``landuse``, ``places``, ``addresses``) sind toter Code:
kein Aufruf von ``osm_layer_path`` verwendet sie. ``places``/``addresses``
waren die Grundlage des früheren OSM-Adress-Cluster-Pfads, den
``03_build_osm_layers.py`` laut eigenem Docstring in v2 explizit
abgeschafft hat ("Kein OSM-Adress-Cluster-Pfad mehr"). Diese Stufe baut
nur die zehn tatsächlich gelesenen Gruppen nach - Regel "Bau genau das
nach, nicht mehr" (vgl. ``pipeline/prep/natur.py``).

``powerlines`` wird extrahiert, obwohl die daraus gebaute Maske
(``power_380_400kv``) in der v2-Kette nirgends persistiert wird
(``INFRA_LAYER_NAMES`` in ``03_build_osm_layers.py`` lässt sie aus) - der
Unterprozessaufruf läuft trotzdem bei jedem Lauf mit, weil
``build_infrastructure_masks()`` ihn unbedingt absetzt. Diese Stufe
reproduziert das tatsächliche Leseverhalten, nicht das, was am Ende
gebraucht würde (Regel 4: keine Änderung an Filtern/Klassifikationen,
und die "Verschwendung" liegt im Konsumenten, der in dieser Welle
unangetastet bleibt).

## Was NICHT nachgebaut wird

- Der bbox-Clip-Schritt (``pbf_for_bounds()``, ein eigener
  ``osmium extract --bbox``-Aufruf VOR dem tags-filter): der dient beim
  Kettenlauf dazu, denselben Ausschnitt für mehrere Layer-Anfragen
  wiederzuverwenden. Diese Stufe verarbeitet ohnehin die volle
  Landesfläche in einem Lauf - ein Clip auf "ganz Österreich + 13 km"
  liefert praktisch dieselbe Datei wie die Rohquelle selbst und würde nur
  Laufzeit kosten, kein anderes Ergebnis.
- Spaltenauswahl (``OSM_PBF_COLUMNS``): welche Spalten ein Aufrufer von
  ``read_layer()`` per ``columns=`` anfordert, unterscheidet sich je
  Konsument (manche, z. B. ``water``, übergeben gar kein ``columns=``).
  Diese Stufe schreibt alle Spalten, die der ``osmium export`` mit dem
  jeweiligen ``include_tags`` ohnehin mitgegeben hat - Spaltenauswahl ist
  Konsumenten-Feinschliff, keine gemeinsame Ableitung.
- Der Null-/Leergeometrie-Filter, den z. B. ``build_osm_building_sources``
  auf den ``buildings``-Layer anwendet (``buildings.geometry.notnull() &
  ~buildings.geometry.is_empty``): das ist konsumentenspezifisch (nur für
  ``buildings``, nicht für die anderen neun Gruppen), keine gemeinsame
  ``read_layer()``-Ableitung - bleibt deshalb Sache des (künftigen)
  Konsumenten.
- Die feingranulare Objektklassifikation (fclass-Filterung auf einzelne
  Werte wie ``motorway``/``trunk`` vs. ``primary``/.../``tertiary``, der
  Tunnel-Ausschluss, die Seilbahn-"people carrying"-Typenliste, die
  Naturschutz-Text-/Tag-Heuristik in ``_build_osm_nature_mask``, die
  Militärflächen-Typenliste) bleibt in den Konsumentenfunktionen
  (``build_infrastructure_masks`` usw.), die in dieser Welle unverändert
  bleiben (Abgrenzung laut Auftrag). Diese Stufe liefert die ungefilterte
  Objektgruppe je Schlüssel - dieselbe Menge, die ``read_layer()`` heute
  aus dem jeweiligen ``osm_layer_path()``-Export liest, nur einmalig und
  ohne bbox-Beschränkung.

## Bandnamen aus PLAN.md §4 vs. tatsächliche Objektgruppen

PLAN.md §4 nennt für die Domäne OSM acht "Erzeugte Layer": roads; rail;
cableway; water_bodies; nature_osm; military; airport; wka_bestand. Das
ist eine grobe, band-orientierte Zusammenfassung, keine 1:1-Liste der
tatsächlich extrahierten Objektgruppen - Unterschiede:

- ``buildings`` und ``powerlines`` fehlen in der PLAN.md-Liste komplett,
  obwohl beide bei jedem Kettenlauf extrahiert werden (siehe oben).
  ``buildings`` speist ``general_buildings_source``/
  ``cableway_buildings_source`` - beide werden in PLAN.md §4 der Domäne
  KATASTER zugeschlagen (Bänder 8-13), obwohl ihre tatsächliche
  OSM-Quelle hier liegt, nicht im DKM-Kataster.
- ``aerialways`` (ungefiltert) bedient ZWEI Konsumenten mit
  unterschiedlicher Nachfilterung: die "cableway"-Distanzmaske (nur
  personenbefördernde Typen, Band 17) UND die Seilbahn-Gebäudenähe für
  ``cableway_buildings_source`` (Band 10, alle Typen). PLAN.md §4 nennt
  nur "cableway" (singular), nicht diese Doppelnutzung.
- ``railways``/``rail``, ``transport``/``airport``, ``windpower``/
  ``wka_bestand``, ``nature``/``nature_osm``, ``water``/``water_bodies``
  entsprechen sich inhaltlich 1:1, tragen aber unterschiedliche Namen als
  osmium-Schlüssel (Code) vs. PLAN.md-Bandfamilie (Dokumentation).

Diese Stufe benennt ihre Ausgabedateien nach den tatsächlichen
Code-Schlüsseln (``OSM_PBF_FILTERS``-Namen), nicht nach den
PLAN.md-Bandfamilien - sonst müsste sie den ``aerialways``-Layer
künstlich aufspalten oder ``buildings``/``powerlines`` unterschlagen, um
auf die Acht-Namen-Liste zu passen. Punkt für §13.1/FORTSCHRITT.md.

## Zuschnitt `pipeline/prep/osm.py` vs. `pipeline/prep/osm/`

PLAN.md §7 nennt als Pfad-Spalte für W1.P5 ``pipeline/prep/osm/`` (mit
Schrägstrich, ein Unterpaket), und ``pipeline/prep/__init__.py`` erwartet
laut eigenem Docstring ebenfalls Unterpakete ``kataster/``, ``osm/``,
``noe/`` für die drei zweistufigen Domänen. Der tatsächliche Auftrag für
dieses Paket verlangt stattdessen eine einzelne flache Datei
``pipeline/prep/osm.py`` neben ``pipeline/prep/__init__.py`` - beide
Stufen als zwei Funktionen in einer Datei statt als zwei Dateien in einem
Unterpaket. Beides ist mit ``contract.PREP["osm"]`` (ein Dict mit
``a_extract``/``b_layers``) vereinbar; das Dict selbst schreibt keine
Dateilayout-Form vor. Abweichung von PLAN.md §7/``__init__.py``
festgehalten, nicht aufgelöst (Regel 6: PLAN.md/FORTSCHRITT.md bleiben in
diesem Paket unangetastet).

## Harte Vorbedingung osmium

``_run_osmium`` ruft ``subprocess.run(cmd, check=True)`` ohne
Fehlerbehandlung auf - fehlt das Kommandozeilenwerkzeug ``osmium``, wirft
das ein ungefangenes ``FileNotFoundError`` und die Stufe bricht ab. Kein
stiller Rückfall auf leere Masken (der existierte nur im Vorgängerprojekt,
nicht in diesem Repo) - siehe Auftrag zu W1.P5.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd

from pipeline import contract, fingerprint, runtime

TARGET_CRS = "EPSG:31287"

# ---------------------------------------------------------------------------
# Wortgleich aus windkraft/calc/abschichtung_common.py übernommen (Zeilen
# ~219, ~327-368) - nur die zehn tatsächlich gelesenen Schlüssel, siehe
# Moduldocstring. Regel 4: Filter/Tags bleiben unverändert: diese Werte sind
# eine Kopie, kein Import, damit diese Prep-Stufe nicht von
# ``windkraft`` (der Konsumentenseite, die diese Welle nicht anfasst)
# abhängt - derselbe Grund, aus dem pipeline/prep/admin.py und
# pipeline/prep/natur.py windkraft nicht importieren.
# ---------------------------------------------------------------------------

WIND_POWER_OSM_FILTERS = ["nwr/generator:source=wind", "nwr/man_made=wind_turbine"]

OSM_PBF_FILTERS: dict[str, list[str]] = {
    "buildings": ["w/building", "r/building"],
    "roads": ["w/highway"],
    "railways": ["w/railway"],
    "powerlines": ["w/power=line", "w/power=minor_line"],
    "transport": ["n/aeroway", "w/aeroway", "r/aeroway"],
    "aerialways": ["n/aerialway", "w/aerialway", "r/aerialway"],
    "military": ["w/landuse=military", "r/landuse=military", "w/military", "r/military"],
    "nature": [
        "w/boundary=protected_area", "r/boundary=protected_area",
        "w/boundary=national_park", "r/boundary=national_park",
        "w/leisure=nature_reserve", "r/leisure=nature_reserve",
        "w/protect_class", "r/protect_class",
        "w/protection_title", "r/protection_title",
    ],
    "windpower": WIND_POWER_OSM_FILTERS,
    "water": [
        "w/natural=water", "r/natural=water",
        "w/waterway=riverbank", "r/waterway=riverbank",
        "w/landuse=reservoir", "r/landuse=reservoir",
    ],
}

OSM_PBF_INCLUDE_TAGS: dict[str, list[str]] = {
    "buildings": ["building"],
    "roads": ["highway", "tunnel"],
    "railways": ["railway", "tunnel"],
    "powerlines": ["power", "voltage"],
    "transport": ["aeroway"],
    "aerialways": ["aerialway"],
    "military": ["landuse", "military"],
    "nature": ["boundary", "leisure", "protect_class", "protection_title", "name"],
    "windpower": ["power", "generator:source", "man_made", "name"],
    "water": ["natural", "water", "waterway", "landuse", "name"],
}

# Reihenfolge = Reihenfolge der Extraktion; nur informativ (dict ist ohnehin
# schon nach OSM_PBF_FILTERS/OSM_PBF_INCLUDE_TAGS-Schlüsseln iterierbar).
LAYER_KEYS = [
    "buildings", "windpower", "aerialways", "powerlines",
    "roads", "railways", "military", "transport", "nature", "water",
]

# Wortgleich aus osm_layer_path() (abschichtung_common.py ~495-501).
_EXPORT_ATTRIBUTES = {
    "type": False, "id": True, "version": False, "changeset": False,
    "timestamp": False, "uid": False, "user": False, "way_nodes": False,
}


def _run_osmium(cmd: list[str]) -> None:
    """Wie abschichtung_common.py:_run_osmium - kein try/except, kein
    stiller Rückfall. Fehlt osmium, propagiert FileNotFoundError."""
    subprocess.run(cmd, check=True)


def _extract_one(pbf_path: Path, key: str, out_dir: Path) -> Path:
    """Ein Objektgruppen-Schlüssel: tags-filter dann export, wie
    osm_layer_path() (Zeile ~504/509), aber ohne bbox-Clip - volle
    Landesfläche in einem Aufruf."""
    filtered = out_dir / f"{key}.osm.pbf"
    exported = out_dir / f"{key}.geojsonseq"

    _run_osmium(["osmium", "tags-filter", str(pbf_path), *OSM_PBF_FILTERS[key], "-O", "-o", str(filtered)])

    export_config = {
        "attributes": _EXPORT_ATTRIBUTES,
        "format_options": {},
        "linear_tags": True,
        "area_tags": True,
        "exclude_tags": [],
        "include_tags": OSM_PBF_INCLUDE_TAGS[key],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as cfg_file:
        json.dump(export_config, cfg_file)
        cfg_path = cfg_file.name
    try:
        _run_osmium(["osmium", "export", str(filtered), "-c", cfg_path, "-O", "-f", "geojsonseq", "-o", str(exported)])
    finally:
        Path(cfg_path).unlink(missing_ok=True)

    return exported


def run_extract(force: bool = False) -> Path:
    """Stufe a: osmium tags-filter + export je Objektgruppe, gegen die volle
    Rohquelle. Teuer (dominiert die Laufzeit der ganzen Stufe)."""
    pbf_path = contract.RAW["osm"]["pbf"]
    out_dir = contract.PREP["osm"]["a_extract"]
    runtime.ensure_dir(out_dir)

    if not force and fingerprint.matches(out_dir, [pbf_path]) and all(
        (out_dir / f"{key}.geojsonseq").exists() for key in LAYER_KEYS
    ):
        print(f"[skip]  prep-osm a_extract: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    for key in LAYER_KEYS:
        print(f"[start] prep-osm a_extract {key}: {' '.join(OSM_PBF_FILTERS[key])}", flush=True)
        _extract_one(pbf_path, key, out_dir)
        print(f"[done]  prep-osm a_extract {key}", flush=True)

    fingerprint.write(out_dir, [pbf_path])
    return out_dir


def _read_exported(path: Path) -> gpd.GeoDataFrame:
    """Wie read_layer() (abschichtung_common.py ~517-546), minus
    bounds-Zuschnitt und Spaltenauswahl - siehe Moduldocstring."""
    empty = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)
    if not path.exists():
        return empty
    # Leere osmium-GeoJSONSeq-Exporte (kein Feature im Ausschnitt) sind 0-1
    # Byte gross und lassen pyogrio mit DataSourceError scheitern - wie
    # read_layer() behandelt das als leerer Layer.
    if path.stat().st_size < 10:
        return empty
    gdf = gpd.read_file(path)
    if gdf.empty:
        return empty
    if "fclass" not in gdf.columns:
        for tag in ("landuse", "highway", "railway", "aeroway", "aerialway"):
            if tag in gdf.columns:
                gdf["fclass"] = gdf[tag]
                break
    if "type" not in gdf.columns and "building" in gdf.columns:
        gdf["type"] = gdf["building"]
    return gdf.to_crs(TARGET_CRS)


def run_layers(force: bool = False) -> Path:
    """Stufe b: pro Objektgruppe read_layer()-Ableitung (fclass/type,
    Reprojektion) einmalig vorrechnen, als GeoParquet. Billig, aber heute
    bei jedem bbox-Aufruf wiederholt (siehe Moduldocstring)."""
    a_dir = contract.PREP["osm"]["a_extract"]
    b_dir = contract.PREP["osm"]["b_layers"]
    runtime.ensure_dir(b_dir)

    inputs = [a_dir / f"{key}.geojsonseq" for key in LAYER_KEYS]
    if not force and fingerprint.matches(b_dir, inputs) and all(
        (b_dir / f"{key}.parquet").exists() for key in LAYER_KEYS
    ):
        print(f"[skip]  prep-osm b_layers: Fingerabdruck unveraendert -> {b_dir}", flush=True)
        return b_dir

    counts: dict[str, int] = {}
    for key in LAYER_KEYS:
        gdf = _read_exported(a_dir / f"{key}.geojsonseq")
        gdf.to_parquet(b_dir / f"{key}.parquet")
        counts[key] = len(gdf)

    fingerprint.write(b_dir, inputs)
    print(
        "[done]  prep-osm b_layers: " + ", ".join(f"{k}={v:,}" for k, v in counts.items()) + f" -> {b_dir}",
        flush=True,
    )
    return b_dir


def run(force: bool = False) -> tuple[Path, Path]:
    a_dir = run_extract(force=force)
    b_dir = run_layers(force=force)
    return a_dir, b_dir


if __name__ == "__main__":
    run()
