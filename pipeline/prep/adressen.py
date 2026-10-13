"""Prep: Adressregister (Paket W1.P3, docs/rewrite/PLAN.md §7, §4).

Einzige Stelle, die das BEV-Adressregister aus den Rohdaten liest
(``contract.RAW["adressen"]["address_dir"]``: entpackte ``ADRESSE.csv``/
``GEBAEUDE.csv`` oder das jüngste ``Adresse_Relationale_Tabellen_
Stichtagsdaten_*.zip``). Die Layer-Stufe liest nur noch die beiden Produkte
(``calc/bev_register.py:load_address_points/load_building_points``); fehlt ein
Produkt, bricht sie mit dem Hinweis auf ``make prep-adressen`` ab - es gibt
keinen Rückfall auf die Roh-CSV mehr (prep-Grenze, CLAUDE.md).

Ausgaben nach ``contract.PREP["adressen"]`` (GeoParquet, EPSG:31287,
Punktgeometrie; die Spalten ``x``/``y`` bleiben zusätzlich erhalten, damit
die Konsumenten wie bisher mit den Koordinaten rechnen):

- ``adressen_31287.parquet``: ``x``, ``y``, ``HNR_ADR_ZUSAMMEN`` (String),
  ``geometry`` (ADRESSE.csv)
- ``bev_gebaeude_31287.parquet``: ``x``, ``y``, ``eigenschaft``, ``geometry``
  (GEBAEUDE.csv)

Koordinaten außerhalb des zulässigen Wertebereichs liefert das BEV als "#";
solche Zeilen werden verworfen. Die Umrechnung aus den drei Gauß-Krüger-
Streifen (RW/HW/EPSG) nach EPSG:31287 geschieht streifenweise.

Fingerabdruck: die tatsächlich gelesenen Rohdateien plus diese Datei
(``pipeline/fingerprint.py``).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import Transformer

from pipeline import contract, fingerprint, runtime
from pipeline.prep.share import skip_without_raw
from calc import bev_register

TARGET_CRS = "EPSG:31287"
TARGET_EPSG = 31287
HNR_COLUMN = "HNR_ADR_ZUSAMMEN"


def _newest_zip(data_dir: Path) -> Path | None:
    candidates = sorted(data_dir.glob("Adresse_Relationale_Tabellen_Stichtagsdaten_*.zip"))
    return candidates[-1] if candidates else None


def _resolved_csv_input(data_dir: Path, name: str) -> Path:
    """Welche Datei ``_read_csv`` für ``name`` tatsächlich liest: die
    Klartext-Datei, sonst das jüngste Stichtags-ZIP."""
    plain = data_dir / name
    if plain.exists():
        return plain
    archive = _newest_zip(data_dir)
    if archive is None:
        raise FileNotFoundError(
            f"Weder {plain} noch ein Adresse_Relationale_Tabellen_Stichtagsdaten_*.zip in {data_dir}"
        )
    return archive


def _read_csv(data_dir: Path, name: str, usecols: list[str]) -> pd.DataFrame:
    """CSV aus dem entpackten Ordner oder direkt aus dem jüngsten Stichtags-ZIP."""
    plain = data_dir / name
    if plain.exists():
        return pd.read_csv(plain, sep=";", usecols=usecols, dtype=str, encoding="utf-8-sig")
    archive = _resolved_csv_input(data_dir, name)
    with zipfile.ZipFile(archive) as zf, zf.open(name) as fh:
        return pd.read_csv(fh, sep=";", usecols=usecols, dtype=str, encoding="utf-8-sig")


def _to_target_crs(df: pd.DataFrame) -> pd.DataFrame:
    """RW/HW/EPSG (GK West/Central/East) -> x/y in EPSG:31287, streifenweise.

    Koordinaten außerhalb des zulässigen Wertebereichs liefert das BEV als "#";
    solche Zeilen werden verworfen statt zu einem Parse-Fehler zu führen.
    """
    rw = pd.to_numeric(df["RW"], errors="coerce")
    hw = pd.to_numeric(df["HW"], errors="coerce")
    epsg = pd.to_numeric(df["EPSG"], errors="coerce")
    ok = rw.notna() & hw.notna() & epsg.notna()
    dropped = int((~ok).sum())
    if dropped:
        print(f"[warn]  BEV: {dropped:,} Zeilen ohne verwertbare Koordinate verworfen", flush=True)
    df = df[ok]
    parts = []
    for code, group in df.groupby(epsg[ok].astype(int)):
        transformer = Transformer.from_crs(int(code), TARGET_EPSG, always_xy=True)
        x, y = transformer.transform(
            pd.to_numeric(group["RW"]).to_numpy(), pd.to_numeric(group["HW"]).to_numpy()
        )
        part = pd.DataFrame({"x": x, "y": y}, index=group.index)
        for col in group.columns:
            if col not in {"RW", "HW", "EPSG"}:
                part[col.lower()] = group[col].to_numpy()
        parts.append(part)
        print(f"[info]  BEV EPSG {code}: {len(group):,} Punkte transformiert", flush=True)
    return pd.concat(parts, ignore_index=True)


def build_address_frame(data_dir: Path) -> pd.DataFrame:
    """DataFrame(x, y, HNR_ADR_ZUSAMMEN) aller BEV-Adresskoordinaten in EPSG:31287.

    ``HNR_ADR_ZUSAMMEN`` ist die zusammengesetzte Hausnummer (String, ein Wert
    je Adresspunkt, fehlende Werte als Null); die Zeilenreihenfolge ist die der
    bisherigen x/y-Tabelle."""
    frame = _to_target_crs(
        _read_csv(data_dir, bev_register.ADDRESS_CSV, ["RW", "HW", "EPSG", HNR_COLUMN])
    )
    return frame.rename(columns={HNR_COLUMN.lower(): HNR_COLUMN})[["x", "y", HNR_COLUMN]]


def build_building_frame(data_dir: Path) -> pd.DataFrame:
    """DataFrame(x, y, eigenschaft) aller BEV-Gebäude in EPSG:31287."""
    frame = _to_target_crs(
        _read_csv(data_dir, bev_register.BUILDING_CSV, ["RW", "HW", "EPSG", "EIGENSCHAFT"])
    )
    return frame[["x", "y", "eigenschaft"]]


def _write_geoparquet(frame: pd.DataFrame, path: Path) -> None:
    gdf = gpd.GeoDataFrame(
        frame, geometry=gpd.points_from_xy(frame["x"], frame["y"]), crs=TARGET_CRS
    )
    gdf.to_parquet(path, index=False)


def run(force: bool = False) -> Path:
    data_dir = contract.RAW["adressen"]["address_dir"]
    out_dir = contract.PREP["adressen"]
    _csv = data_dir / bev_register.ADDRESS_CSV
    _raw_probe = _csv if _csv.exists() else (
        _newest_zip(data_dir) or data_dir / "Adresse_Relationale_Tabellen_Stichtagsdaten_*.zip"
    )
    if not force and skip_without_raw(
        "adressen", [_raw_probe], hint="data/adressen/ (BEV Adresse_Relationale_Tabellen_Stichtagsdaten_*.zip)"
    ):
        return out_dir
    runtime.ensure_dir(out_dir)

    inputs = sorted(
        {
            _resolved_csv_input(data_dir, bev_register.ADDRESS_CSV),
            _resolved_csv_input(data_dir, bev_register.BUILDING_CSV),
        }
    )
    # Path(__file__) zaehlt zum Fingerabdruck mit (W6.4, Punkt 45): eine
    # Aenderung an dieser Datei soll den Selbst-Ueberspringer aufheben, nicht
    # nur eine Aenderung an data/. Konservativ - nur die eigene Quelldatei,
    # nicht die Importe (siehe pipeline/fingerprint.py).
    inputs.append(Path(__file__))
    address_path = contract.PREP_FILES["adressen"]["adressen"]
    building_path = contract.PREP_FILES["adressen"]["gebaeude"]

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers). `--force` erzwingt einen Neulauf.
    if (
        not force
        and address_path.exists()
        and building_path.exists()
        and fingerprint.matches(out_dir, inputs)
    ):
        print(f"[skip]  prep-adressen: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    address_frame = build_address_frame(data_dir)
    _write_geoparquet(address_frame, address_path)
    print(f"[info]  BEV-Adressen: {len(address_frame):,} -> {address_path}", flush=True)

    building_frame = build_building_frame(data_dir)
    _write_geoparquet(building_frame, building_path)
    print(f"[info]  BEV-Gebäude: {len(building_frame):,} -> {building_path}", flush=True)

    fingerprint.write(out_dir, inputs)

    print(
        f"[done]  prep-adressen: {len(address_frame):,} Adresspunkte, "
        f"{len(building_frame):,} Gebäudepunkte -> {out_dir}",
        flush=True,
    )
    return out_dir


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
