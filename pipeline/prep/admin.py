"""Prep: Verwaltungsgrenzen (Paket W1.P1, docs/rewrite/PLAN.md §7, §4).

Liest die VGD-Rohquelle (``contract.RAW["admin"]["vgd"]`` - ein Shapefile
auf Katastralgemeinde-Ebene mit 7850 Zeilen, siehe ``docs/rewrite/nachweise/
w01p1/``) genau einmal und schreibt zwei Ableitungen nach
``contract.PREP["admin"]``:

- ``gemeinden.gpkg`` - Dissolve nach ``GKZ`` (Gemeindekennziffer): die
  tatsächlichen 2093 politischen Gemeinden. Verlustfrei, weil PG/BL/BL_KZ/
  PB/BKZ je GKZ konstant sind (geprüft, siehe Bericht zu W1.P1) - "first"
  beim Dissolve nimmt also nichts Uneindeutiges weg.
- ``bundesland_masken.gpkg`` - Dissolve nach ``BL``: dieselbe Operation,
  die ``calc/abschichtung_common.py`` heute bei *jedem* Aufruf
  von ``official_wind_zoning_mask`` erneut auf einem bounds-gefilterten
  Ausschnitt rechnet (Zeile ~1351: ``bl.dissolve(by="BL").reset_index()``).
  Hier einmalig auf dem vollen Datensatz vorgerechnet - Rasterisierung
  betrifft ohnehin nur das Canvas des jeweiligen Grids, ein Dissolve auf
  mehr Fläche als nötig ändert also kein Ergebnis, nur die Laufzeit
  verschiebt sich von "bei jedem Aufruf" auf "einmal in der Prep-Stufe".

Beide Ausgaben liegen in EPSG:31287 - die Rohquelle ist es bereits
(``to_crs`` unten ist ein Sicherheitsnetz, kein tatsächliches Reprojizieren
bei dieser Quelle), siehe PLAN.md §7, Abnahme von W1.P1.

Was diese Stufe NICHT tut: sie filtert nicht nach ``bounds`` (das bleibt
Sache der Konsumenten, vgl. ``read_layer(..., bounds=...)``), und sie
ändert keine Werte, Puffer oder Schwellwerte (Regel 4). Die Konsumenten
lesen in dieser Welle weiterhin die Rohdatei - die Umstellung auf dieses
Prep-Ergebnis ist Aufgabe von Welle 2 (siehe PLAN.md §3).
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

from pipeline import contract, fingerprint, runtime

TARGET_CRS = "EPSG:31287"

GEMEINDEN_FILENAME = "gemeinden.gpkg"
BUNDESLAND_MASKEN_FILENAME = "bundesland_masken.gpkg"

# Nur diese Spalten überleben den Gemeinden-Dissolve (Katastralgemeinde-
# spezifische Spalten wie KG_NR/KG/FL wären nach dem Dissolve nur noch die
# "erste" von mehreren Katastralgemeinden und damit irreführend).
GEMEINDEN_COLUMNS = ["GKZ", "PG", "BKZ", "PB", "BL_KZ", "BL", "geometry"]


def _shapefile_sidecars(shp_path: Path) -> list[Path]:
    """Alle Begleitdateien eines Shapefiles (.shp/.shx/.dbf/.prj/.cpg/...).

    ``contract.RAW["admin"]["vgd"]`` deklariert nur die ``.shp``-Datei, aber
    ein Shapefile ist ohne seine Geschwisterdateien nicht lesbar bzw. nicht
    dasselbe - .dbf trägt die Attribute, .prj das CRS. Der Fingerabdruck
    muss alle erfassen, sonst bliebe eine geänderte .dbf unbemerkt.
    """
    return sorted(p for p in shp_path.parent.glob(shp_path.stem + ".*") if p.is_file())


def run(force: bool = False) -> Path:
    vgd_path = contract.RAW["admin"]["vgd"]
    out_dir = contract.PREP["admin"]
    runtime.ensure_dir(out_dir)

    # Path(__file__) zaehlt zum Fingerabdruck mit (W6.4, Punkt 45): eine
    # Aenderung an dieser Datei soll den Selbst-Ueberspringer aufheben, nicht
    # nur eine Aenderung an data/. Konservativ - nur die eigene Quelldatei,
    # nicht die Importe (siehe pipeline/fingerprint.py).
    inputs = _shapefile_sidecars(vgd_path) + [Path(__file__)]
    gemeinden_path = out_dir / GEMEINDEN_FILENAME
    bundesland_path = out_dir / BUNDESLAND_MASKEN_FILENAME

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    # docs/rewrite/PLAN.md). `--force` erzwingt einen Neulauf.
    if (
        not force
        and gemeinden_path.exists()
        and bundesland_path.exists()
        and fingerprint.matches(out_dir, inputs)
    ):
        print(f"[skip]  prep-admin: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    gdf = gpd.read_file(vgd_path)
    if gdf.crs is None or str(gdf.crs).upper() != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)

    gemeinden = gdf.dissolve(by="GKZ", aggfunc="first").reset_index()[GEMEINDEN_COLUMNS]
    gemeinden.to_file(gemeinden_path, driver="GPKG")

    bundeslaender = gdf.dissolve(by="BL").reset_index()[["BL", "geometry"]]
    bundeslaender.to_file(bundesland_path, driver="GPKG")

    fingerprint.write(out_dir, inputs)

    print(
        f"[done]  prep-admin: {len(gemeinden)} Gemeinden, "
        f"{len(bundeslaender)} Bundesländer -> {out_dir}",
        flush=True,
    )
    return out_dir


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
