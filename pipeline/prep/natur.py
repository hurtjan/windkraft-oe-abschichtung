"""Prep: Naturschutz (Paket W1.P7, docs/rewrite/PLAN.md §7, §4).

Liest die Naturschutz-Rohquelle (``contract.RAW["natur"]["nsg_zip"]`` -
das ZIP-Archiv ``SG_AT_2024_v_April_Stand_3_April_2024.zip``, 73 MB laut
PLAN.md §4) genau einmal und schreibt die Ableitung nach
``contract.PREP["natur"]``: eine einzelne GeoParquet-Datei
(``schutzgebiete.parquet``) mit den Geometrien der fünf Schutzgebietslayer,
in EPSG:31287.

Was heute tatsächlich gelesen wird (``calc/abschichtung_common.py``,
``_build_official_nature_mask``, Zeile ~1160-1194) - dieses Modul baut
GENAU das nach, nicht mehr:

- Das GeoPackage-Mitglied im ZIP heißt ``SG_AT_2024_v_April.gpkg``
  (``config.json:paths.nsg_gpkg``) und wird bei jedem Kettenlauf neu in
  ein Temp-Verzeichnis entpackt.
- Grundsatz (Nutzerentscheidung, gilt unabhängig von der Datenquelle):
  Der Natur-Ausschluss umfasst Schutzkategorien, die nach dem
  Naturschutzrecht der Länder per Verordnung ODER Bescheid festgelegt
  sind, ohne Abstand. Prädikate und Programme ohne eigenen Schutzstatus
  (Naturpark, Biosphärenpark, UNESCO, IUCN-Einstufungen) schließen nicht
  aus, ebenso wenig jagdrechtliche Wildruheflächen und die Empfehlungen
  „Schutzzonen Bergwelt Tirol". Ein weiterer Layer kommt mit einer Zeile
  in ``config.json:paths.nsg_layers`` dazu, ein weiterer Code mit einem
  Eintrag in ``paths.nsg_layer_filter``.
- Das GeoPackage-Mitglied im ZIP heißt ``SG_AT_2024_v_April.gpkg``
  (``config.json:paths.nsg_gpkg``) und wird bei jedem Kettenlauf neu in
  ein Temp-Verzeichnis entpackt.
- Grundsatz (Nutzerentscheidung, gilt unabhängig von der Datenquelle):
  Der Natur-Ausschluss umfasst nur Schutzkategorien, die nach dem
  Naturschutzrecht der Länder per Verordnung festgelegt sind. Prädikate
  und Programme ohne eigenen Schutzstatus (Naturpark, Biosphärenpark,
  UNESCO, IUCN-Einstufungen) schließen nicht aus, ebenso wenig
  jagdrechtliche Wildruheflächen und die Empfehlungen „Schutzzonen
  Bergwelt Tirol". Per Bescheid festgelegte Kleinkategorien (geschützte
  Biotope GB, örtliche Schutzgebiete ÖSG, ÖE, GNÖB, GLR) und
  Naturdenkmäler (NDKM) sind vorerst nicht enthalten; ein weiterer Layer
  kommt mit einer Zeile in ``config.json:paths.nsg_layers`` dazu, ein
  weiterer Code mit einem Eintrag in ``paths.nsg_layer_filter``.
- Das GeoPackage-Mitglied im ZIP heißt ``SG_AT_2024_v_April.gpkg``
  (``config.json:paths.nsg_gpkg``) und wird bei jedem Kettenlauf neu in
  ein Temp-Verzeichnis entpackt.
- Gelesen werden die Layer aus ``config.json:paths.nsg_layers``:
  ``NP_AT_2024`` (Nationalparke), ``NSG_AT_2024`` (Naturschutzgebiete),
  ``ESG_AT_2024`` (Europaschutzgebiete/Natura 2000), ``RAMSAR_AT_2024``,
  ``LSG_AT_2024`` (Landschaftsschutzgebiete, nur aus UBA, nie aus OSM),
  ``GLT_AT_2024`` (geschützte Landschaftsteile), ``NDKM_AT_2024``
  (Naturdenkmäler: Polygone sowie Punkt-/MultiPunkt-Objekte, kein Puffer)
  und ``S_AT_2024`` (sonstige Schutzgebiete) - letzterer gefiltert über
  ``paths.nsg_layer_filter`` auf ``KAT_SUB`` in RG (Ruhegebiete), RZ
  (Ruhezone), PSG (Pflanzenschutzgebiete), SSG, SAFM, ``SG §26`` sowie die
  Bescheid-Kategorien GB (geschützte Biotope), GLR, GNÖB, ÖE und ÖSG
  (örtliche Schutzgebiete). Nur die von UBA als nicht gültig markierten
  Codes SGNOG und SZSFFG fehlen (kommen im Layer nicht vor).
  Rasterung (Konsument, ``raster_mask`` mit ``all_touched=True``):
  Punktobjekte belegen ihre 25-m-Zelle, Flächen jede berührte Zelle.
  Nicht verwendet: IUCN-Kategorien, Biosphärenparke, Naturparke,
  UNESCO-Gebiete (kein eigener Schutzstatus).
- Je Layer werden die Geometrie sowie ``KAT`` und ``KAT_SUB`` (soweit
  vorhanden) und der Quelllayer (``quelle``) übernommen, zur
  Nachvollziehbarkeit; der Konsument braucht nur die Geometrie. Der
  Filter ist Teil des Fingerabdrucks (``config.json`` zählt mit).
- Die Layer werden konkateniert und mit dem CRS des ERSTEN Layers
  versehen (``parts[0].crs`` im Original) - bei der heutigen Quelle sind
  alle fünf Layer EPSG:3035, das ist also kein Informationsverlust.
- Ein Null-/Leer-Geometrie-Filter (``notnull() & ~is_empty``) läuft mit,
  obwohl er bei der heutigen Quelle keine Wirkung hat (siehe Bericht zu
  W1.P7 - 0 Null-/Leergeometrien in den ersten vier Layern; LSG_AT_2024 vor dem Neulauf zu prüfen). Ungültige
  Geometrien (nicht simple Polygone) werden NICHT repariert - der
  Konsument tut das auch nicht (Regel 4: keine Werteänderung).
- Reprojektion nach EPSG:31287 (``TARGET_CRS`` im Original) mit
  ``to_crs``.

Was diese Stufe NICHT tut: sie filtert NICHT auf ``grid["bounds"]`` (der
Konsument schneidet erst danach auf die Rastergitter-Bounding-Box zu,
``nature.geometry.intersects(box(*grid["bounds"]))``) - das bleibt Sache
des Konsumenten, exakt wie bei ``pipeline/prep/admin.py`` (vgl. dessen
Docstring). Sie fängt auch keine Lesefehler defensiv ab und degradiert
nicht still auf eine leere Maske, wie es der Konsument bei fehlendem ZIP
oder nicht lesbarem Layer tut (``return np.zeros(...)`` bzw. ein
Warnhinweis und Weiterlaufen ohne den Layer) - eine Prep-Stufe soll laut
Entscheidung (c) (PLAN.md §5) hart scheitern statt still mit
unvollständigen Zwischenständen weiterzurechnen; bei der tatsächlichen
Eingabedatei tritt der Unterschied nicht in Erscheinung (alle fünf Layer
lesen sich anstandslos).

Die Konsumenten (pipeline/layers/geo.py) lesen ausschließlich dieses
Prep-Ergebnis; je Feature bleiben die Spalten ``layer`` (UBA-Layername),
``quelle`` (identisch), ``KAT`` und ``KAT_SUB`` erhalten. Zeilenzahl je Layer:
NP 29, NSG 499, ESG 368, RAMSAR 24, LSG 277, GLT 325, S (gefiltert) 58,
NDKM 4 517 (1 414 davon Point/MultiPoint).
"""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from pipeline import contract, fingerprint, runtime
from pipeline.prep.share import skip_without_raw

TARGET_CRS = "EPSG:31287"

OUTPUT_FILENAME = contract.PREP_FILES["natur"]["schutzgebiete"].name

# Projekt-Wurzel, um config.json unabhängig vom Arbeitsverzeichnis zu
# finden (pipeline/prep/natur.py liegt zwei Ebenen darunter).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"


def _read_gpkg_member_and_layers() -> tuple[str, list[str], dict[str, dict[str, list[str]]]]:
    """Liest ``nsg_gpkg`` (ZIP-Mitgliedsname) und ``nsg_layers``
    (Layernamen) aus ``config.json`` - das sind laut
    ``pipeline/contract.py`` (Kommentar bei ``RAW["natur"]``) bewusst
    KEINE Pfade und stehen deshalb nicht im Pfadvertrag, sondern bleiben
    Nicht-Pfad-Parameter in ``config.json``. Diese Stufe liest sie von
    dort, statt sie hier ein zweites Mal als Literal zu erfinden - genau
    dieselbe Quelle, die ``_build_official_nature_mask`` heute über
    ``cfg["paths"]`` bekommt.
    """
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    return paths["nsg_gpkg"], list(paths["nsg_layers"]), dict(paths.get("nsg_layer_filter", {}))


def apply_layer_filter(gdf: gpd.GeoDataFrame, filt: dict[str, list[str]] | None) -> gpd.GeoDataFrame:
    """Behält nur Zeilen, deren Attribut in der Liste steht (je Spalte
    ``isin``; mehrere Spalten werden mit UND verknüpft). Ohne Filter
    unverändert. Fehlt die Spalte, scheitert die Stufe hart (KeyError)."""
    if not filt:
        return gdf
    keep = pd.Series(True, index=gdf.index)
    for col, allowed in filt.items():
        keep &= gdf[col].isin(allowed)
    return gdf[keep]


def build_schutzgebiete(
    frames: dict[str, gpd.GeoDataFrame], layer_filter: dict[str, dict[str, list[str]]] | None = None
) -> gpd.GeoDataFrame:
    """Eine Zeile je Quell-Feature (nach ``KAT_SUB``-Filter), kein Dissolve,
    keine Pufferung, Original-Geometrietypen (NDKM-Punkte bleiben Punkte).

    Spalten: ``layer`` (UBA-Layername, z. B. ``NP_AT_2024``), ``KAT``,
    ``KAT_SUB`` (soweit vorhanden), ``quelle`` (gleich ``layer``, für ältere
    Leser) und ``geometry``. CRS: das des ersten nicht leeren Layers.
    """
    parts = []
    for layer, gdf in frames.items():
        gdf = apply_layer_filter(gdf, (layer_filter or {}).get(layer))
        if not gdf.empty:
            cols = [c for c in ("KAT", "KAT_SUB") if c in gdf.columns]
            part = gdf[[*cols, "geometry"]].copy()
            part["layer"] = layer
            part["quelle"] = layer
            parts.append(part)
    out = gpd.GeoDataFrame(
        pd.concat(parts, ignore_index=True), geometry="geometry", crs=parts[0].crs
    )
    cols = ["layer", *[c for c in ("KAT", "KAT_SUB") if c in out.columns], "quelle", "geometry"]
    return out[cols]


def run(force: bool = False) -> Path:
    zip_path = contract.RAW["natur"]["nsg_zip"]
    out_dir = contract.PREP["natur"]
    if not force and skip_without_raw("natur", [zip_path], hint="data/natur/ (Schutzgebiets-ZIP SG_AT_2024…)"):
        return out_dir
    runtime.ensure_dir(out_dir)

    # CONFIG_PATH zaehlt zum Fingerabdruck mit, nicht nur zip_path: diese
    # Stufe liest daraus tatsaechlich ``nsg_gpkg``/``nsg_layers`` (siehe
    # ``_read_gpkg_member_and_layers``) - aendert sich die Layerauswahl dort,
    # ohne dass sich das ZIP aendert, waere ein reiner zip_path-Fingerabdruck
    # blind dafuer.
    # Path(__file__) zaehlt zum Fingerabdruck mit (W6.4, Punkt 45): eine
    # Aenderung an dieser Datei soll den Selbst-Ueberspringer aufheben, nicht
    # nur eine Aenderung an data/. Konservativ - nur die eigene Quelldatei,
    # nicht die Importe (siehe pipeline/fingerprint.py).
    inputs = [zip_path, CONFIG_PATH, Path(__file__)]
    out_path = contract.PREP_FILES["natur"]["schutzgebiete"]

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    # docs/rewrite/PLAN.md). `--force` erzwingt einen Neulauf.
    if not force and out_path.exists() and fingerprint.matches(out_dir, inputs):
        print(f"[skip]  prep-natur: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    gpkg_member, layer_names, layer_filter = _read_gpkg_member_and_layers()

    frames: dict[str, gpd.GeoDataFrame] = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path) as z:
            z.extract(gpkg_member, tmpdir)
        gpkg_path = Path(tmpdir) / gpkg_member
        for layer in layer_names:
            frames[layer] = gpd.read_file(gpkg_path, layer=layer)

    schutzgebiete = build_schutzgebiete(frames, layer_filter)
    schutzgebiete = schutzgebiete[
        schutzgebiete.geometry.notnull() & ~schutzgebiete.geometry.is_empty
    ]
    schutzgebiete = schutzgebiete.to_crs(TARGET_CRS)

    schutzgebiete.to_parquet(out_path, index=False)

    fingerprint.write(out_dir, inputs)

    print(
        f"[done]  prep-natur: {len(schutzgebiete)} Schutzgebietsflächen "
        f"aus {len(layer_names)} Layern -> {out_path}",
        flush=True,
    )
    return out_dir


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
