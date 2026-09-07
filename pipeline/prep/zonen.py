"""Prep: Windzonen (Paket W1.P8, docs/rewrite/PLAN.md §7, §4).

Liest die vier verbliebenen Positivzonen-Quellen, die heute über
``windkraft.calc.wind_zones.WIND_ZONE_SOURCES`` in Band ``official_wind_zoning``
einfließen (siehe dessen Moduldocstring: die frühere Ausschlusszonen-
Registrierung - Negativband ``official_wind_exclusion_zoning``,
``load_wind_exclusion_zones()``, ``WIND_EXCLUSION_ZONE_SOURCES`` - ist in
W1.5 entfernt worden, weil das Band im 38-Band-Schema nicht existiert und
die Ladefunktion nirgends aufgerufen wurde) und schreibt je Quelle eine
eigene, normalisierte Ableitung nach ``contract.PREP["zonen"]``:

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

Jede Quelle wird nach ``EPSG:31287`` reprojiziert (``wind_zones.TARGET_CRS``)
und wie in ``wind_zones._clean_geometries()`` bereinigt: leere/Null-
Geometrien verworfen, ungültige mit ``buffer(0)`` repariert.

Die Lese-/Filter-/CRS-Logik ist hier bewusst UNABHÄNGIG von
``windkraft/calc/wind_zones.py`` nachgebaut (kein Import von dort) - der
Gleichheitsnachweis in der Abnahme vergleicht zwei getrennte Lesungen
derselben Rohdaten, nicht dieselbe Funktion mit sich selbst.

Was diese Stufe NICHT tut:

- Sie klippt NICHT auf die zuständige Bundesland-Grenze
  (``wind_zones._clip_to_bundesland()``). Das passiert in der Kette erst
  beim eigentlichen Bandbau (``abschichtung_common.py:
  build_official_zoning_masks``), mit den grid-bounds-gefilterten
  Verwaltungsgrenzen als zusätzlicher, hier nicht verfügbarer Eingabe -
  Sache der Konsumenten, die diese Welle nicht anfasst (Abgrenzung laut
  Auftrag: ``wind_zones.py`` bleibt, wie W1.5 es hinterlassen hat).
- Sie fasst ``data/zonen/zonierung_noe.json``
  (``contract.RAW["zonen"]["official_zoning_noe"]``) NICHT an: diese Quelle
  läuft nicht über ``WIND_ZONE_SOURCES``, sondern wird in
  ``abschichtung_common.py`` direkt per ``--official-zoning-geojson``
  gelesen - ein eigener Codepfad außerhalb dieses Auftrags (Auftrag nennt
  explizit nur Stmk/Sbg/Bgld/RED3).
- Sie fasst keine Werte, Puffer, Klassifikationen oder Präfixe an
  (Regel 4) - ``Status``/``Eignungszone`` bleiben exakt wie im Original.

Jede der vier Quellen ist eine harte Vorbedingung: fehlt eine Datei oder
liefert sie nach Filter/Bereinigung keine Geometrie, bricht der Lauf ab
statt still zu überspringen (anders als ``wind_zones._resolve_path()``,
das bei fehlender Datei nur warnt - siehe dessen Kommentare zu Bgld/RED3).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd

from pipeline import contract, fingerprint, runtime

TARGET_CRS = "EPSG:31287"

# Muss zu windkraft.calc.wind_zones.WIND_ZONE_SOURCES (Bgld-Eintrag) passen -
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


# Reihenfolge ist die Ausgabereihenfolge im Log - inhaltlich unabhängig,
# jede Quelle bekommt ihre eigene Datei.
SOURCES = {
    "Stmk": _load_stmk,
    "Sbg": _load_sbg,
    "Bgld": _load_bgld,
    "RED3": _load_red3,
}


def _fingerprint_inputs() -> list[Path]:
    zonen = contract.RAW["zonen"]
    luca_dir = zonen["luca_zonen_dir"]
    inputs = [zonen["eignungszonen_zip"], zonen["red3_zip"]]
    for stem in ("Stmk", "Sbg"):
        inputs.extend(sorted(p for p in luca_dir.glob(stem + ".*") if p.is_file()))
    return sorted(inputs)


def run() -> Path:
    out_dir = contract.PREP["zonen"]
    runtime.ensure_dir(out_dir)

    counts: dict[str, tuple[int, float]] = {}
    for key, loader in SOURCES.items():
        gdf = loader()
        if gdf.empty:
            raise ValueError(
                f"wind zone source '{key}' liefert nach Filter/Bereinigung keine Geometrie"
            )
        gdf.to_file(out_dir / f"{key}.gpkg", driver="GPKG")
        counts[key] = (len(gdf), float(gdf.area.sum()) / 1e6)

    fingerprint.write(out_dir, _fingerprint_inputs())

    summary = ", ".join(f"{k}: n={n}, {area:.1f} km²" for k, (n, area) in counts.items())
    print(f"[done]  prep-zonen: {summary} -> {out_dir}", flush=True)
    return out_dir


if __name__ == "__main__":
    run()
