"""BEV-Adressregister ("Adresse Relationale Tabellen - Stichtagsdaten") einlesen.

Liefert zwei Punktwolken in EPSG:31287. Das Einlesen der Rohdaten (CSV/ZIP,
Umprojizieren der 2,5 Mio Zeilen aus drei Gauß-Krüger-Streifen) passiert
ausschließlich in pipeline/prep/adressen.py (prep-Grenze, CLAUDE.md); dieses
Modul liest nur noch die beiden prep-Produkte (GeoParquet):

``load_address_points``   ADRESSE.csv  -> (N, 2) Koordinaten. Das "es gibt hier
                          eine Adresse"-Signal der Hüllen-Klassifikation.
``load_building_points``  GEBAEUDE.csv -> DataFrame(x, y, eigenschaft). Zusätzlich
                          zur Koordinate die *überwiegende Eigenschaft* des
                          Gebäudes, aus der der Wohnanteil einer Hülle kommt.

ACHTUNG - Abweichung vom Plan (§4.3): Der Wohnfunktions-Anteil kommt NICHT aus
GEBAEUDE_FUNKTION.csv. Deren ``OBJFUNKTKENNZIFFER`` ist eine Sonderfunktionsliste
(01 Apotheke, 03 Polizei, 04 Feuerwehr, 08 Schule ...) mit "99 = zur Zeit keine
Funktion zugeordnet" für praktisch alle Zeilen - kein Wohn-Signal. Das
tatsächliche Nutzungsfeld ist ``GEBAEUDE.EIGENSCHAFT`` (siehe EIGENSCHAFT_*
unten), und es steht in derselben Zeile wie die Koordinate, sodass der im Plan
vorgesehene Join über GEBAEUDE.csv entfällt.

Der Datensatz hat datierte Dateinamen (Stichtage 1.4. / 1.10.); das jeweils
jüngste ZIP wird in der prep-Stufe automatisch genommen.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import contract

TARGET_EPSG = 31287

ADDRESS_CACHE_NAME = contract.PREP_FILES["adressen"]["adressen"].name
BUILDING_CACHE_NAME = contract.PREP_FILES["adressen"]["gebaeude"].name

ADDRESS_CSV = "ADRESSE.csv"
BUILDING_CSV = "GEBAEUDE.csv"

# GEBAEUDE.EIGENSCHAFT - "Überwiegende Eigenschaft dieses Objektes"
EIGENSCHAFT_WOHNUNG_EINE = "01"
EIGENSCHAFT_WOHNUNG_MEHRERE = "02"
EIGENSCHAFT_WOHNGEMEINSCHAFT = "03"
EIGENSCHAFT_HOTEL = "04"
EIGENSCHAFT_BUERO = "05"
EIGENSCHAFT_HANDEL = "06"
EIGENSCHAFT_VERKEHR = "07"
EIGENSCHAFT_INDUSTRIE_LAGER = "08"
EIGENSCHAFT_KULTUR_BILDUNG = "09"

# Was als "Wohnen" zählt. Hotels (04) bewusst NICHT: Ferienhaus-/Tourismus-
# gebiete bekommen über die Widmung ihre eigene 750-m-Kategorie, und ein
# reines Hotelareal soll den vollen Wohn-Nachweis nicht ersetzen.
RESIDENTIAL_EIGENSCHAFTEN = frozenset({
    EIGENSCHAFT_WOHNUNG_EINE,
    EIGENSCHAFT_WOHNUNG_MEHRERE,
    EIGENSCHAFT_WOHNGEMEINSCHAFT,
})
INDUSTRIAL_EIGENSCHAFTEN = frozenset({EIGENSCHAFT_INDUSTRIE_LAGER})


def _read_prepared(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"BEV-Adressregister-Produkt fehlt: {path} - zuerst 'make prep-adressen' "
            "(das Einlesen der Rohdaten gehört ausschließlich in pipeline/prep/adressen.py)."
        )
    return pd.read_parquet(path, columns=columns)


def load_address_points(path: Path | None = None) -> np.ndarray:
    """(N, 2)-Array aller BEV-Adresskoordinaten in EPSG:31287, aus dem
    prep-Produkt (GeoParquet ``derived/prep/adressen/adressen_31287.parquet``).
    Fehlt es, bricht der Aufruf ab - kein Rückfall auf die Rohdaten."""
    path = Path(path) if path is not None else contract.PREP_FILES["adressen"]["adressen"]
    frame = _read_prepared(path, ["x", "y"])
    print(f"[info]  BEV-Adressen: {len(frame):,} Punkte aus {path}", flush=True)
    return frame[["x", "y"]].to_numpy()


def load_building_points(path: Path | None = None) -> pd.DataFrame:
    """DataFrame(x, y, eigenschaft) aller BEV-Gebäude in EPSG:31287, aus dem
    prep-Produkt (``derived/prep/adressen/bev_gebaeude_31287.parquet``)."""
    path = Path(path) if path is not None else contract.PREP_FILES["adressen"]["gebaeude"]
    frame = _read_prepared(path, ["x", "y", "eigenschaft"])
    print(f"[info]  BEV-Gebäude: {len(frame):,} Punkte aus {path}", flush=True)
    return frame


def residential_flags(eigenschaft: pd.Series | np.ndarray) -> np.ndarray:
    return pd.Series(eigenschaft).isin(RESIDENTIAL_EIGENSCHAFTEN).to_numpy()


def industrial_flags(eigenschaft: pd.Series | np.ndarray) -> np.ndarray:
    return pd.Series(eigenschaft).isin(INDUSTRIAL_EIGENSCHAFTEN).to_numpy()
