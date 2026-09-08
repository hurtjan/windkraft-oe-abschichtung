"""Prep: Windzonen (Paket W1.P8, docs/rewrite/PLAN.md §7, §4; um die fünfte
Quelle NÖ erweitert - Punkt 22 in ``docs/rewrite/FORTSCHRITT.md``, ebenfalls
§7 - siehe Kommentar bei ``_load_noe()``).

Liest die fünf Positivzonen-Quellen, die heute in Band
``official_wind_zoning`` einfließen - vier über
``calc.wind_zones.WIND_ZONE_SOURCES`` (siehe dessen Moduldocstring:
die frühere Ausschlusszonen-Registrierung - Negativband
``official_wind_exclusion_zoning``, ``load_wind_exclusion_zones()``,
``WIND_EXCLUSION_ZONE_SOURCES`` - ist in W1.5 entfernt worden, weil das Band
im 38-Band-Schema nicht existiert und die Ladefunktion nirgends aufgerufen
wurde), die fünfte über einen eigenen Codepfad in
``abschichtung_common.build_official_zoning_masks()`` - und schreibt je
Quelle eine eigene, normalisierte Ableitung nach ``contract.PREP["zonen"]``:

- ``Stmk.gpkg``, ``Sbg.gpkg`` - direkt aus
  ``<luca_zonen_dir>/<Stmk|Sbg>.shp`` (kein eigener ``source_path`` in der
  Registrierung -> ``<zone_dir>/<key>.shp``).
- ``Bgld.gpkg`` - aus ``data/zonen/WK_Eignungszonen.zip``, über
  ``zip://<pfad>!<innerer Shapefile-Name>`` gelesen (kein Entpacken auf
  Platte - GDAL/OGR liest per VSIZIP direkt aus dem Archiv, wie es
  ``wind_zones._resolve_path()`` heute schon tut). Attributfilter
  ``Status`` beginnt mit ``Eignungszone`` - die Datei enthält im selben
  Layer 40 Eignungs- UND 31 Ausschlusszonen (gemessen, siehe Abnahmebericht),
  ohne den Filter würden Ausschlusszonen ins Positivband rutschen.
- ``RED3.gpkg`` - aus ``data/zonen/RED_III_Windkraftbeschleunigungszone.zip``,
  ebenfalls per ``zip://``, ohne Attributfilter.
- ``NOE.gpkg`` - aus ``data/zonen/zonierung_noe.json``
  (``contract.RAW["zonen"]["official_zoning_noe"]``), 71 niederösterreichische
  Zonen, EPSG:4326 im Rohformat. Läuft in der Kette NICHT über
  ``WIND_ZONE_SOURCES``, sondern wird per Kommandozeilenschalter
  ``--official-zoning-geojson`` direkt in
  ``abschichtung_common.build_official_zoning_masks()`` über die dortige
  generische ``read_layer()`` gelesen (Definition dort, Zeile ~517) - kein
  eigener, benannter Loader in ``wind_zones.py`` wie bei den anderen vier.
  Punkt 22: weder die Domänentabelle noch der Zuschnitt von W1.P8 hatten
  diese Quelle erfasst.

Jede der vier ``WIND_ZONE_SOURCES``-Quellen wird nach ``EPSG:31287``
reprojiziert (``wind_zones.TARGET_CRS``) und wie in
``wind_zones._clean_geometries()`` bereinigt: leere/Null-Geometrien
verworfen, ungültige mit ``buffer(0)`` repariert. Die NÖ-Quelle wird nur
reprojiziert, NICHT bereinigt - ``read_layer()``, ihr tatsächlicher
Produktivpfad, tut das ebenfalls nicht (siehe ``_load_noe()``). Auf den
aktuellen Rohdaten macht das keinen Unterschied (0 invalide/leere/Null-
Geometrien gemessen), aber einen Bereinigungsschritt einzuführen, den die
laufende Funktion nicht hat, wäre eine Verbesserung und keine Überführung
(Regel 4).

Die Lese-/Filter-/CRS-Logik der vier ``WIND_ZONE_SOURCES``-Quellen ist hier
bewusst UNABHÄNGIG von ``calc/wind_zones.py`` nachgebaut (kein
Import von dort) - der Gleichheitsnachweis in der Abnahme vergleicht zwei
getrennte Lesungen derselben Rohdaten, nicht dieselbe Funktion mit sich
selbst. Für die NÖ-Quelle war der stärkere Nachweis möglich (vgl. W1.P1 vs.
W1.P7 in ``docs/rewrite/FORTSCHRITT.md``): ``read_layer()`` ist - anders als
die privaten, rasterisierenden Konsumenten aus W1.P7 - eine öffentliche,
direkt aufrufbare Funktion; der Gleichheitsnachweis ruft sie tatsächlich auf
(siehe Abnahmebericht). ``_load_noe()`` unten bleibt trotzdem ein
unabhängiger Nachbau, aus Konsistenz mit den anderen vier Quellen dieses
Moduls - der stärkere Weg steckt im *Vergleich*, nicht im Modulcode.

Was diese Stufe NICHT tut:

- Sie klippt NICHT auf die zuständige Bundesland-Grenze
  (``wind_zones._clip_to_bundesland()``). Das passiert in der Kette erst
  beim eigentlichen Bandbau (``abschichtung_common.py:
  build_official_zoning_masks``), mit den grid-bounds-gefilterten
  Verwaltungsgrenzen als zusätzlicher, hier nicht verfügbarer Eingabe -
  Sache der Konsumenten, die diese Welle nicht anfasst (Abgrenzung laut
  Auftrag: ``wind_zones.py`` bleibt, wie W1.5 es hinterlassen hat).
- Sie filtert die NÖ-Quelle NICHT nach ``bounds`` - genau wie
  ``pipeline/prep/admin.py`` das für seine Quelle offen lässt (siehe dessen
  Docstring): Bounds-Filterung bleibt Sache der Konsumenten
  (``read_layer(..., bounds=grid["bounds"])``). Der Gleichheitsnachweis
  ruft ``read_layer()`` deshalb ohne ``bounds`` auf.
- Sie fasst keine Werte, Puffer, Klassifikationen oder Präfixe an
  (Regel 4) - ``Status``/``Eignungszone`` bleiben exakt wie im Original,
  und für die NÖ-Quelle werden bis auf die Geometrie alle Sachattribute
  (``ZONE``, ``LEGALFOUNDATIONDATE``, ...) verworfen - wie bei den anderen
  vier Quellen dieses Moduls, deren einziger Konsument (Rasterisierung zu
  einer Maske) sie ohnehin nicht braucht.

Jede der fünf Quellen ist eine harte Vorbedingung: fehlt eine Datei oder
liefert sie nach Filter/Bereinigung keine Geometrie, bricht der Lauf ab
statt still zu überspringen (anders als ``wind_zones._resolve_path()``, das
bei fehlender Datei nur warnt - siehe dessen Kommentare zu Bgld/RED3 - und
anders als ``read_layer()``, das bei fehlender Datei eine leere
GeoDataFrame statt eines Fehlers liefert).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import geopandas as gpd

from pipeline import contract, fingerprint, runtime

TARGET_CRS = "EPSG:31287"

# Muss zu calc.wind_zones.WIND_ZONE_SOURCES (Bgld-Eintrag) passen -
# absichtlich hier neu erklärt statt importiert, siehe Moduldocstring.
BGLD_FILTER_FIELD = "Status"
BGLD_KEEP_PREFIX = "Eignungszone"


def _inner_shapefile(zip_path: Path) -> str:
    """Name der einzigen .shp im Zip - bricht hart ab, wenn keine da ist."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
    if not names:
        raise ValueError(f"wind zone zip enthält keine .shp: {zip_path}")
    return names[0]


def _read_zip_shapefile(zip_path: Path) -> gpd.GeoDataFrame:
    """Liest das gezippte Shapefile per GDAL-VSIZIP - kein Entpacken auf Platte."""
    if not zip_path.exists():
        raise FileNotFoundError(f"wind zone source fehlt: {zip_path}")
    inner = _inner_shapefile(zip_path)
    return gpd.read_file(f"zip://{zip_path}!{inner}")


def _clean_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Wie wind_zones._clean_geometries(): leere/Null-Geometrien raus,
    ungültige per buffer(0) reparieren, ohne die Eingabe zu mutieren."""
    out = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    if out.empty:
        return out
    invalid = ~out.geometry.is_valid
    if invalid.any():
        out.loc[invalid, "geometry"] = out.geometry[invalid].buffer(0)
    return out[out.geometry.notnull() & ~out.geometry.is_empty]


def _load_luca_zonen_shp(key: str) -> gpd.GeoDataFrame:
    shp = contract.RAW["zonen"]["luca_zonen_dir"] / f"{key}.shp"
    if not shp.exists():
        raise FileNotFoundError(f"wind zone source fehlt: {shp}")
    gdf = gpd.read_file(shp)
    return _clean_geometries(gdf.to_crs(TARGET_CRS))[["geometry"]]


def _load_stmk() -> gpd.GeoDataFrame:
    return _load_luca_zonen_shp("Stmk")


def _load_sbg() -> gpd.GeoDataFrame:
    return _load_luca_zonen_shp("Sbg")


def _load_bgld() -> gpd.GeoDataFrame:
    gdf = _read_zip_shapefile(contract.RAW["zonen"]["eignungszonen_zip"])
    if BGLD_FILTER_FIELD not in gdf.columns:
        raise KeyError(
            f"wind zone source 'Bgld' erwartet Attribut '{BGLD_FILTER_FIELD}' "
            f"(vorhanden: {sorted(gdf.columns)})"
        )
    values = gdf[BGLD_FILTER_FIELD].astype("string").fillna("")
    gdf = gdf[values.str.startswith(BGLD_KEEP_PREFIX).fillna(False)]
    return _clean_geometries(gdf.to_crs(TARGET_CRS))[["geometry"]]


def _load_red3() -> gpd.GeoDataFrame:
    gdf = _read_zip_shapefile(contract.RAW["zonen"]["red3_zip"])
    return _clean_geometries(gdf.to_crs(TARGET_CRS))[["geometry"]]


def _load_noe() -> gpd.GeoDataFrame:
    """Fünfte Quelle, Punkt 22: ``zonierung_noe.json``, in der Kette gelesen
    von ``abschichtung_common.read_layer()``, nicht von ``wind_zones.py``.

    Nachgebaut wird hier genau das, was ``read_layer(path)`` ohne ``where``,
    ``columns`` und ``bounds`` tatsächlich tut: Datei lesen, nach
    ``TARGET_CRS`` reprojizieren. Die dortigen fclass/type-Attribut-
    Ableitungen greifen nicht (die Rohdatei hat weder ``landuse``/
    ``highway``/... noch ``building`` als Spalte, gemessen), und eine
    Bounds-Filterung entfällt, weil ohne ``bounds`` aufgerufen (siehe
    Moduldocstring: Bounds bleiben Sache der Konsumenten). Anders als die
    vier ``WIND_ZONE_SOURCES``-Loader oben wird NICHT über
    ``_clean_geometries()`` bereinigt - ``read_layer()`` tut das auch nicht.
    """
    path = contract.RAW["zonen"]["official_zoning_noe"]
    if not path.exists():
        raise FileNotFoundError(f"wind zone source fehlt: {path}")
    gdf = gpd.read_file(path)
    return gdf.to_crs(TARGET_CRS)[["geometry"]]


# Reihenfolge ist die Ausgabereihenfolge im Log - inhaltlich unabhängig,
# jede Quelle bekommt ihre eigene Datei.
SOURCES = {
    "Stmk": _load_stmk,
    "Sbg": _load_sbg,
    "Bgld": _load_bgld,
    "RED3": _load_red3,
    "NOE": _load_noe,
}


def _fingerprint_inputs() -> list[Path]:
    zonen = contract.RAW["zonen"]
    luca_dir = zonen["luca_zonen_dir"]
    inputs = [
        zonen["eignungszonen_zip"],
        zonen["red3_zip"],
        zonen["official_zoning_noe"],
    ]
    for stem in ("Stmk", "Sbg"):
        inputs.extend(sorted(p for p in luca_dir.glob(stem + ".*") if p.is_file()))
    # Path(__file__) zaehlt zum Fingerabdruck mit (W6.4, Punkt 45): eine
    # Aenderung an dieser Datei soll den Selbst-Ueberspringer aufheben, nicht
    # nur eine Aenderung an data/. Konservativ - nur die eigene Quelldatei,
    # nicht die Importe (siehe pipeline/fingerprint.py).
    inputs.append(Path(__file__))
    return sorted(inputs)


def run(force: bool = False) -> Path:
    out_dir = contract.PREP["zonen"]
    runtime.ensure_dir(out_dir)

    inputs = _fingerprint_inputs()
    output_paths = [out_dir / f"{key}.gpkg" for key in SOURCES]

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    # docs/rewrite/PLAN.md). `--force` erzwingt einen Neulauf.
    if (
        not force
        and all(p.exists() for p in output_paths)
        and fingerprint.matches(out_dir, inputs)
    ):
        print(f"[skip]  prep-zonen: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    counts: dict[str, tuple[int, float]] = {}
    for key, loader in SOURCES.items():
        gdf = loader()
        if gdf.empty:
            raise ValueError(
                f"wind zone source '{key}' liefert nach Filter/Bereinigung keine Geometrie"
            )
        gdf.to_file(out_dir / f"{key}.gpkg", driver="GPKG")
        counts[key] = (len(gdf), float(gdf.area.sum()) / 1e6)

    fingerprint.write(out_dir, inputs)

    summary = ", ".join(f"{k}: n={n}, {area:.1f} km²" for k, (n, area) in counts.items())
    print(f"[done]  prep-zonen: {summary} -> {out_dir}", flush=True)
    return out_dir


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
