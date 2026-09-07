"""Prep: Naturschutz (Paket W1.P7, docs/rewrite/PLAN.md §7, §4).

Liest die Naturschutz-Rohquelle (``contract.RAW["natur"]["nsg_zip"]`` -
das ZIP-Archiv ``SG_AT_2024_v_April_Stand_3_April_2024.zip``, 73 MB laut
PLAN.md §4) genau einmal und schreibt die Ableitung nach
``contract.PREP["natur"]``: eine einzelne GeoPackage-Datei
(``schutzgebiete.gpkg``) mit den Geometrien der vier Schutzgebietslayer,
in EPSG:31287.

Was heute tatsächlich gelesen wird (``windkraft/calc/abschichtung_common.py``,
``_build_official_nature_mask``, Zeile ~1160-1194) - dieses Modul baut
GENAU das nach, nicht mehr:

- Das GeoPackage-Mitglied im ZIP heißt ``SG_AT_2024_v_April.gpkg``
  (``config.json:paths.nsg_gpkg``) und wird bei jedem Kettenlauf neu in
  ein Temp-Verzeichnis entpackt.
- Nur vier der 20 Layer im GeoPackage werden gelesen
  (``config.json:paths.nsg_layers``): ``NP_AT_2024`` (Nationalparke),
  ``NSG_AT_2024`` (Naturschutzgebiete), ``ESG_AT_2024`` (Europaschutz-
  gebiete/Natura 2000) und ``RAMSAR_AT_2024`` (Ramsar-Feuchtgebiete).
  Die übrigen 16 Layer (Landschaftsschutzgebiete, IUCN-Kategorien,
  Biosphärenparke, UNESCO-Gebiete, ...) werden vom Konsumenten nicht
  angefasst und bleiben deshalb auch hier außen vor - das nachzuziehen
  wäre "mehr", als die Kette heute tut, und Sache von Welle 2, falls
  gewünscht.
- Je Layer wird NUR die Geometriespalte übernommen
  (``gdf[["geometry"]]``) - alle Sachattribute (``UBA_ID``, ``BL``,
  ``KAT``, ``SG_NAME``, ``Flache_ha``, ...) werden vom Konsumenten sofort
  verworfen, weil er nur eine binäre Rastermaske braucht. Diese Stufe
  reproduziert exakt das: geometrieonly, kein Sachattribut überlebt.
- Die vier Layer werden konkateniert und mit dem CRS des ERSTEN Layers
  versehen (``parts[0].crs`` im Original) - bei der heutigen Quelle sind
  alle vier Layer EPSG:3035, das ist also kein Informationsverlust.
- Ein Null-/Leer-Geometrie-Filter (``notnull() & ~is_empty``) läuft mit,
  obwohl er bei der heutigen Quelle keine Wirkung hat (siehe Bericht zu
  W1.P7 - 0 Null-/Leergeometrien in allen vier Layern). Ungültige
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
Eingabedatei tritt der Unterschied nicht in Erscheinung (alle vier Layer
lesen sich anstandslos).

Die Konsumenten lesen in dieser Welle weiterhin die Rohdatei direkt - die
Umstellung auf dieses Prep-Ergebnis ist Aufgabe von Welle 2 (PLAN.md §3).
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from pipeline import contract, fingerprint, runtime

TARGET_CRS = "EPSG:31287"

OUTPUT_FILENAME = "schutzgebiete.gpkg"

# Projekt-Wurzel, um config.json unabhängig vom Arbeitsverzeichnis zu
# finden (pipeline/prep/natur.py liegt zwei Ebenen darunter).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"


def _read_gpkg_member_and_layers() -> tuple[str, list[str]]:
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
    return paths["nsg_gpkg"], list(paths["nsg_layers"])


def run() -> Path:
    zip_path = contract.RAW["natur"]["nsg_zip"]
    out_dir = contract.PREP["natur"]
    runtime.ensure_dir(out_dir)

    gpkg_member, layer_names = _read_gpkg_member_and_layers()

    parts = []
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path) as z:
            z.extract(gpkg_member, tmpdir)
        gpkg_path = Path(tmpdir) / gpkg_member
        for layer in layer_names:
            gdf = gpd.read_file(gpkg_path, layer=layer)
            if not gdf.empty:
                parts.append(gdf[["geometry"]])

    schutzgebiete = gpd.GeoDataFrame(
        pd.concat(parts, ignore_index=True), geometry="geometry", crs=parts[0].crs
    )
    schutzgebiete = schutzgebiete[
        schutzgebiete.geometry.notnull() & ~schutzgebiete.geometry.is_empty
    ]
    schutzgebiete = schutzgebiete.to_crs(TARGET_CRS)

    out_path = out_dir / OUTPUT_FILENAME
    schutzgebiete.to_file(out_path, driver="GPKG")

    fingerprint.write(out_dir, [zip_path])

    print(
        f"[done]  prep-natur: {len(schutzgebiete)} Schutzgebietsflächen "
        f"aus {len(layer_names)} Layern -> {out_path}",
        flush=True,
    )
    return out_dir


if __name__ == "__main__":
    run()
