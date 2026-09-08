"""Prep: Flächenwidmung (Paket W1.P4, docs/rewrite/PLAN.md §7, §4).

Neun Bundesländer, neun Rohformate (ZIP/SHP, GPKG, GeoJSON - siehe
``calc/widmung_sources.py:DATASETS``). Diese Stufe normalisiert
genau das, was die Kette heute tatsächlich tut, um daraus drei
bundesland-übergreifende Bündel zu bauen - nicht mehr und nicht weniger
(Regel 4: Widmungsklassen, Attributfilter, Klassifikationen bleiben
unverändert, auch wo sie zwischen Bundesländern inkonsistent aussehen).

Die tatsächlich laufende Funktion ist ``build_all_buckets`` in
``scripts/widmung_v2/01_build_official_zoning_layers.py`` (Skript 1 von 3
der Widmung-Kette). Dieses Modul importiert von dort nichts - der
Dateiname beginnt mit einer Ziffer und ist kein gültiger Python-Bezeichner,
ein Import über ``sys.path``-Präambel wäre ein Umweg um das eigentliche
Ziel dieser Welle (siehe PLAN.md §1.8, toter Entry-Point). Stattdessen
baut ``_build_all_buckets`` unten dieselbe Orchestrierung nach: dieselbe
Schleife über ``DATASETS`` (ein Lesevorgang je Rohdatei, auch wenn z. B.
Oberösterreich sieben Quellen speist), dieselbe Anwendung von
``source_mask`` je ``SOURCES``-Eintrag, dieselbe Gruppierung nach
``BUCKETS``. Jede fachliche Entscheidung (welcher Code zu welcher Klasse
gehört, welches Feld gefiltert wird) bleibt ausschließlich in
``calc/widmung_sources.py`` - hier wird nur importiert, nie neu
klassifiziert.

Die drei Bündel (``wohn_misch``, ``haeuser_im_gruenen``,
``industrie_negativ`` - siehe ``calc/widmung_sources.py:BUCKETS``
für die fachliche Bedeutung) entstehen als
``<bucket>_combined.gpkg`` unter ``contract.PREP["widmung"]`` - derselbe
Dateiname wie damals (historisch, vor W6.1) im Zwischenstand unter
``output/abschichtung_widmung_v2/zoning_vectors/`` (dieses output/ existiert
seit W6.1 nicht mehr im Repo), damit ein späterer
Konsument (Welle 2) ohne Umbenennung umgestellt werden kann.

``read_dataset`` (aus ``widmung_sources.py``) macht bereits die gesamte
Normalisierung je Rohdatei: Nullgeometrien raus, ``to_crs(EPSG:31287)``,
AT-Bbox-Clip (Steiermark-OGD-Verschiebungsartefakte). Diese Stufe ändert
daran nichts, sie ruft nur auf.

Fingerabdruck: die zehn tatsächlich gelesenen Rohdateien (neun
Bundesländer, Steiermark zweifach - Bauland.zip UND Flaewi.shp.zip, siehe
Auftrag). Kärnten wird intern aus dem ZIP in einen lokalen Cache entpackt
(``_ensure_ktn_gpkg`` in ``widmung_sources.py``, wegen /vsizip-Performance
auf GeoPackages) - der Fingerabdruck erfasst trotzdem das ZIP selbst
(``contract.RAW["widmung"]["kaernten"]``), nicht die entpackte Kopie: das
ZIP ist die tatsächliche Rohquelle, die Entpackung ein Implementierungs-
detail von ``widmung_sources.py``, das diese Stufe nicht anfasst. Tirol
hat einen Stichtag im Dateinamen und wird per Glob aufgelöst
(``widmung_sources._tirol_gpkg``) - dieselbe Auflösungsfunktion wird hier
aufgerufen statt ein zweites Mal nachgebaut (vgl. W1.P3/``adressen.py`` und
``bev_register._newest_zip``).

Was diese Stufe NICHT tut: sie ändert ``widmung_sources.py`` nicht
(Abgrenzung dieser Welle), sie dissolved nicht (genau wie das Originalskript
- rasterize() in Skript 3 behandelt überlappende Polygone vor und nach
einem Dissolve identisch, ein Dissolve hier würde nur Zeit kosten und die
Pro-Feature-Provenienz verlieren), und sie ändert keine Werte, Puffer oder
Codelisten (Regel 4).
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from pipeline import contract, fingerprint, runtime
from calc import widmung_sources as ws

BUNDLE_FILENAME = "{bucket}_combined.gpkg"


def _build_all_buckets(cache_dir: Path) -> dict[str, gpd.GeoDataFrame]:
    """Wie ``build_all_buckets`` in
    ``scripts/widmung_v2/01_build_official_zoning_layers.py`` (alle
    Bundesländer, alle drei Buckets) - eine Datei je Datensatz, einmal
    gelesen, dann je Quelle gefiltert und nach Bucket gruppiert.
    """
    frames: dict[str, list[gpd.GeoDataFrame]] = {b: [] for b in ws.BUCKETS}
    for dataset_key in ws.DATASETS:
        wanted = ws.sources_for_dataset(dataset_key)
        if not wanted:
            continue
        gdf = ws.read_dataset(dataset_key, cache_dir)
        for src in wanted:
            selected = gdf[ws.source_mask(gdf, src)]
            if selected.empty:
                print(f"[warn]  {src['key']}: source filter returned no features")
                continue
            frame = gpd.GeoDataFrame(geometry=selected.geometry.reset_index(drop=True), crs=ws.WORK_CRS)
            frame["bundesland"] = ws.bundesland_of(src)
            frame["source_layer"] = src["key"]
            frame["category"] = src["category"]
            frames[src["bucket"]].append(frame)
            print(f"[{src['key']}] {ws.bundesland_of(src)} / {src['category']}: {len(frame):,} Flächen")

    out: dict[str, gpd.GeoDataFrame] = {}
    for bucket, parts in frames.items():
        if parts:
            out[bucket] = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=ws.WORK_CRS)
        else:
            out[bucket] = gpd.GeoDataFrame(
                {"bundesland": [], "source_layer": [], "category": []}, geometry=[], crs=ws.WORK_CRS
            )
    return out


def _raw_input_for_dataset(dataset_key: str) -> Path:
    """Die tatsächlich gelesene Rohdatei je Datensatz-Schlüssel.

    Für neun der zehn Schlüssel steht das direkt in
    ``contract.RAW["widmung"]``. Tirol ist die Ausnahme: der Dateiname
    trägt einen Stichtag, aufgelöst per Glob - dieselbe Funktion, die
    ``widmung_sources._read_raw`` selbst benutzt.
    """
    raw = contract.RAW["widmung"]
    mapping = {
        "bgld": raw["burgenland"],
        "ktn": raw["kaernten"],
        "noe": raw["niederoesterreich"],
        "ooe": raw["oberoesterreich"],
        "sbg": raw["salzburg"],
        "stmk_bauland": raw["steiermark_bauland"],
        "stmk_flaewi": raw["steiermark_flaewi"],
        "vbg": raw["vorarlberg"],
        "wien": raw["wien"],
    }
    if dataset_key == "tir":
        return ws._tirol_gpkg()
    return mapping[dataset_key]


def run(force: bool = False) -> Path:
    out_dir = contract.PREP["widmung"]
    runtime.ensure_dir(out_dir)
    cache_dir = runtime.ensure_dir(out_dir / "_cache")

    inputs = sorted({_raw_input_for_dataset(key) for key in ws.DATASETS})
    # Path(__file__) zaehlt zum Fingerabdruck mit (W6.4, Punkt 45): eine
    # Aenderung an dieser Datei soll den Selbst-Ueberspringer aufheben, nicht
    # nur eine Aenderung an data/. Konservativ - nur die eigene Quelldatei,
    # nicht die Importe (siehe pipeline/fingerprint.py).
    inputs.append(Path(__file__))
    bundle_paths = [out_dir / BUNDLE_FILENAME.format(bucket=b) for b in ws.BUCKETS]

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    # docs/rewrite/PLAN.md). `--force` erzwingt einen Neulauf.
    if (
        not force
        and all(p.exists() for p in bundle_paths)
        and fingerprint.matches(out_dir, inputs)
    ):
        print(f"[skip]  prep-widmung: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    built = _build_all_buckets(cache_dir)

    total = 0
    for bucket, gdf in built.items():
        path = out_dir / BUNDLE_FILENAME.format(bucket=bucket)
        gdf.to_file(path, layer=bucket, driver="GPKG")
        km2 = gdf.geometry.area.sum() / 1e6
        total += len(gdf)
        print(f"[done]  prep-widmung: {bucket}: {len(gdf):,} Flächen, {km2:,.1f} km² -> {path}", flush=True)

    fingerprint.write(out_dir, inputs)

    print(f"[done]  prep-widmung: {total:,} Flächen gesamt -> {out_dir}", flush=True)
    return out_dir


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
