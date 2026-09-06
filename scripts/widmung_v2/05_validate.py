"""Testpunkt-Validierung der Widmungs-Abschichtung v2 (Plan Phase 3).

Prüft an den im Plan festgelegten Orten, ob die v2-Bänder das erwartete Ergebnis
liefern - jeder Punkt steht für eine Entscheidung, die v2 gegenüber v1 ändert:

  Schwaig / Meilersdorf / Aschauer  NÖ-SekROP-PDF-Zonen greifen (RRU_WI_HUELLE
                                    kennt dort nichts)
  Steinbrunn See (B)                Ferienhaus-Widmung 10030 -> 750 m statt 1.200 m
  St. Peter/Linz (OÖ)               Industriegebiet -> 25 m trotz 479 Adressen
  Seefeld (T)                       Tourismusgebiet § 40 (4) -> 750 m
  Poggersdorf (K)                   WIDG-Datenloch, die Streusiedlungs-Hülle
                                    trägt -> 750 m
  Einzelhof bei Eisenkappel (K)     bewohnt, aber < 5 adressierte Objekte ->
                                    Einzellage: seit dem Clean-Schema (Aug 2026)
                                    Teil von general_buildings (25 m)

Bandnamen entsprechen dem Clean-Schema (Aug 2026): HiG-Familie als
haeuser_im_gruenen_* + Aggregat haeuser_im_gruenen; Einzellagen in
general_buildings; die frühere Kategorie important_objects ist entfallen.

Gelesen werden entweder die Checkpoint-Raster eines --layer-dir oder die Bänder
eines fertigen --tif. Punkte außerhalb des Rasterausschnitts werden übersprungen
(SKIP), damit dasselbe Skript für bbox-Smoke-Tests und den Vollauslauf passt.

Run:  uv run python scripts/analysis/validate_hig_v2.py --layer-dir output/abschichtung_widmung_v2/distance_layers
      uv run python scripts/analysis/validate_hig_v2.py --tif output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Erwartungen je Testpunkt: Bandname -> erwarteter Wert (1 = gesetzt, 0 = nicht).
# Nur Bänder aufführen, die der Punkt tatsächlich belegt - alles andere bleibt frei.
TEST_POINTS = [
    {
        "name": "Schwaig (NÖ Mostviertel)",
        "bundesland": "Niederösterreich",
        "xy": (491542, 458896),
        "expect": {"haeuser_im_gruenen_noe_pdf": 1, "haeuser_im_gruenen": 1},
        "note": "in PDF-Zone -> 750-m-Ausschluss",
    },
    {
        "name": "Meilersdorf (NÖ)",
        "bundesland": "Niederösterreich",
        "xy": (498458, 468387),
        "expect": {"haeuser_im_gruenen_noe_pdf": 1, "haeuser_im_gruenen": 1},
        "note": "in PDF-Zone",
    },
    {
        "name": "Aschauer (NÖ Waldviertel)",
        "bundesland": "Niederösterreich",
        "xy": (562683, 518066),
        "expect": {"haeuser_im_gruenen_noe_pdf": 1, "haeuser_im_gruenen": 1},
        "note": "PDF-Zone + Gho",
    },
    {
        "name": "Steinbrunn See (B)",
        "bundesland": "Burgenland",
        "xy": (628228, 441814),
        "expect": {"haeuser_im_gruenen_ferienhaus": 1, "official_settlement_source": 0,
                   "haeuser_im_gruenen": 1},
        "note": "Ferienhaus-Widmung 10030 -> 750 m, NICHT 1.200 m",
    },
    {
        # Die positive Erwartung (nonresidential_hulls_source == 1) ist wichtig:
        # ein reines "haeuser_im_gruenen_streusiedlung == 0" wäre auch dann
        # erfüllt, wenn der DKM-Scan gar nichts geliefert hat - genau so
        # verdeckte dieser Testpunkt zunächst den Bundesland-Umschrift-Bug.
        "name": "St. Peter/Linz (OÖ)",
        "bundesland": "Oberösterreich",
        "xy": (474412, 486888),
        "expect": {"nonresidential_hulls_source": 1, "haeuser_im_gruenen_streusiedlung": 0},
        "note": "industriegebietartig -> 25-m-Band statt 750-m-Band",
    },
    {
        "name": "Seefeld (T)",
        "bundesland": "Tirol",
        "xy": (238117, 383601),
        "expect": {"haeuser_im_gruenen_ferienhaus": 1, "haeuser_im_gruenen": 1},
        "note": "Tourismusgebiet § 40 (4) -> 750 m",
    },
    {
        "name": "Poggersdorf (K, WIDG-Loch)",
        "bundesland": "Kärnten",
        "xy": (485584, 306233),
        "expect": {"haeuser_im_gruenen_streusiedlung": 1, "haeuser_im_gruenen": 1},
        "note": "Streusiedlungs-Hülle (401 Adressen >= Schwelle) -> 750 m (Widmungsloch geheilt)",
    },
    {
        # Kern der Streusiedlungs-Regel (Knie-Analyse): bewohnt, aber nur EINE
        # Adresse -> keine Streusiedlung; die Einzellage steckt seit dem
        # Clean-Schema in general_buildings (25 m). Der Punkt liegt > 25 km von
        # der nächsten Streusiedlungs-Hülle und > 800 m von jeder anderen
        # 750-m-Quelle - haeuser_im_gruenen MUSS hier 0 sein.
        "name": "Einzelhof bei Eisenkappel (K)",
        "bundesland": "Kärnten",
        "xy": (511800, 291225),
        "expect": {"general_buildings_source": 1, "haeuser_im_gruenen_streusiedlung": 0,
                   "general_buildings_buffer": 1, "haeuser_im_gruenen": 0},
        "note": "bewohnte Einzellage (1 Adresse < Schwelle) -> 25 m über general_buildings",
    },
]


class BandReader:
    """Einheitlicher Zugriff auf Bänder, egal ob Einzel-TIFs oder Multiband-TIF."""

    def __init__(self, layer_dir: Path | None, tif: Path | None):
        self.layer_dir = layer_dir
        self.dataset = rasterio.open(tif) if tif else None
        self.band_index = {}
        if self.dataset is not None:
            for idx, desc in enumerate(self.dataset.descriptions, start=1):
                if desc:
                    self.band_index[desc] = idx

    def close(self) -> None:
        if self.dataset is not None:
            self.dataset.close()

    def available(self, band: str) -> bool:
        if self.dataset is not None:
            return band in self.band_index
        return (self.layer_dir / f"{band}.tif").exists()

    def value_at(self, band: str, xy: tuple[float, float]) -> int | None:
        """Bandwert am Punkt, oder None wenn der Punkt außerhalb liegt."""
        if self.dataset is not None:
            src, index = self.dataset, self.band_index[band]
            return self._sample(src, index, xy)
        with rasterio.open(self.layer_dir / f"{band}.tif") as src:
            return self._sample(src, 1, xy)

    @staticmethod
    def _sample(src, index: int, xy: tuple[float, float]) -> int | None:
        row, col = src.index(*xy)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None
        window = rasterio.windows.Window(col, row, 1, 1)
        return int(src.read(index, window=window)[0, 0])


def check_point(reader: BandReader, point: dict) -> tuple[str, list[str]]:
    """(Status, Detailzeilen) für einen Testpunkt."""
    details = []
    failures = 0
    outside = 0
    missing = 0
    for band, expected in point["expect"].items():
        if not reader.available(band):
            details.append(f"    {band}: BAND FEHLT")
            missing += 1
            continue
        actual = reader.value_at(band, point["xy"])
        if actual is None:
            details.append(f"    {band}: außerhalb des Rasters")
            outside += 1
            continue
        ok = int(actual > 0) == int(expected > 0)
        details.append(f"    {band}: erwartet {expected}, ist {actual}  {'OK' if ok else 'FEHLER'}")
        failures += 0 if ok else 1
    if outside and not failures:
        return "SKIP", details
    if missing:
        return "MISSING", details
    return ("PASS" if failures == 0 else "FAIL"), details


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Testpunkte der Widmungs-Abschichtung v2 prüfen.")
    p.add_argument("--layer-dir", default="output/abschichtung_widmung_v2/distance_layers")
    p.add_argument("--tif", default=None, help="Statt Einzel-Checkpoints ein fertiges Multiband-GeoTIFF prüfen")
    p.add_argument("--bl", action="append", default=None, help="Nur Testpunkte dieser Bundesländer (wiederholbar)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reader = BandReader(Path(args.layer_dir) if args.layer_dir else None,
                        Path(args.tif) if args.tif else None)
    wanted = set(args.bl) if args.bl else None
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "MISSING": 0}
    try:
        for point in TEST_POINTS:
            if wanted and point["bundesland"] not in wanted:
                continue
            status, details = check_point(reader, point)
            counts[status] += 1
            print(f"[{status:7}] {point['name']} @ {point['xy']} - {point['note']}")
            for line in details:
                print(line)
    finally:
        reader.close()

    print("\n" + " | ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if counts["FAIL"] or counts["MISSING"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
