"""Prep: Adressregister (Paket W1.P3, docs/rewrite/PLAN.md §7, §4).

Vorgeschichte (siehe Docstring von ``calc/bev_register.py`` und
PLAN.md §7, Paket W1.1): Bis W1.1 hatte ``bev_register.py`` eine
Cache-Weiche, die den aus ``cache_dir`` berechneten Pfad überschrieb, sobald
die Cache-Datei direkt in ``data_dir`` lag - nach dem ersten produktiven
Lauf also immer. ``cache_dir`` war damit wirkungslos, der Cache landete
still im Rohdatenbaum. Seit W1.1 gilt ``cache_dir or
contract.PREP["adressen"]`` - der Parameter wirkt tatsächlich, und beide
Parquet-Dateien entstehen unter ``derived/prep/adressen/``.

Was bis hierher fehlte: ein **eigener, aufrufbarer Schritt**. Ohne dieses
Paket entsteht der Cache nur als Nebenprodukt des ersten Kettenlaufs, der
zufällig ``load_address_points``/``load_building_points`` aufruft - kein
Fingerabdruck, kein Nachweis, dass die Eingabe seither unverändert ist.

Diese Stufe ruft deshalb genau die **tatsächlich laufenden** Funktionen aus
``calc/bev_register.py`` auf (``load_address_points``,
``load_building_points``, unverändert - siehe Abgrenzung im Bericht zu
W1.P3) - mit ``rebuild=True``, damit ein Prep-Lauf den Cache-Stand
tatsächlich neu erzeugt statt nur einen vorhandenen Treffer zu lesen - und
schreibt danach einen Fingerabdruck (``pipeline/fingerprint.py``, der
gemeinsame Mechanismus, kein eigener) der Dateien, die dabei tatsächlich
gelesen wurden.

"Tatsächlich gelesen" ist hier nicht trivial: ``bev_register._read_csv``
liest ``ADRESSE.csv``/``GEBAEUDE.csv`` als Klartext, falls vorhanden, sonst
aus dem jüngsten ``Adresse_Relationale_Tabellen_Stichtagsdaten_*.zip`` im
selben Verzeichnis (``bev_register._newest_zip``). Welche der beiden
Quellen tatsächlich greift, hängt vom Stand von ``data/adressen`` ab -
diese Stufe fragt exakt dieselbe Auflösungsfunktion ab, statt sie ein
zweites Mal zu implementieren (Bug-Gefahr bei zwei Kopien derselben Regel).

Was diese Stufe NICHT tut: sie ändert ``bev_register.py`` nicht (Abgrenzung
dieser Welle - die Konsumenten bleiben, wie W1.1 sie hinterlassen hat) und
ändert keine Werte oder Schwellwerte (Regel 4).
"""

from __future__ import annotations

import sys
from pathlib import Path

from pipeline import contract, fingerprint, runtime
from calc import bev_register


def _resolved_csv_input(data_dir: Path, name: str) -> Path:
    """Welche Datei ``bev_register._read_csv`` für ``name`` tatsächlich liest.

    Ruft dieselbe (private) Auflösungsfunktion auf, die
    ``bev_register._read_csv`` selbst verwendet, statt die Regel
    ("Klartext-Datei, sonst jüngstes Stichtags-ZIP") hier ein zweites Mal
    nachzubauen - zwei Kopien derselben Regel könnten auseinanderlaufen.
    """
    plain = data_dir / name
    if plain.exists():
        return plain
    archive = bev_register._newest_zip(data_dir)
    if archive is None:
        raise FileNotFoundError(
            f"Weder {plain} noch ein Adresse_Relationale_Tabellen_Stichtagsdaten_*.zip in {data_dir}"
        )
    return archive


def run(force: bool = False) -> Path:
    data_dir = contract.RAW["adressen"]["address_dir"]
    out_dir = contract.PREP["adressen"]
    runtime.ensure_dir(out_dir)

    inputs = sorted(
        {
            _resolved_csv_input(data_dir, bev_register.ADDRESS_CSV),
            _resolved_csv_input(data_dir, bev_register.BUILDING_CSV),
        }
    )
    address_path = out_dir / bev_register.ADDRESS_CACHE_NAME
    building_path = out_dir / bev_register.BUILDING_CACHE_NAME

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese Stufe nicht neu rechnen - insbesondere
    # nicht das teure ``rebuild=True`` unten (Punkt 52, docs/rewrite/
    # PLAN.md). `--force` erzwingt einen Neulauf.
    if (
        not force
        and address_path.exists()
        and building_path.exists()
        and fingerprint.matches(out_dir, inputs)
    ):
        print(f"[skip]  prep-adressen: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return out_dir

    address_points = bev_register.load_address_points(data_dir, cache_dir=out_dir, rebuild=True)
    building_points = bev_register.load_building_points(data_dir, cache_dir=out_dir, rebuild=True)

    fingerprint.write(out_dir, inputs)

    print(
        f"[done]  prep-adressen: {len(address_points):,} Adresspunkte, "
        f"{len(building_points):,} Gebäudepunkte -> {out_dir}",
        flush=True,
    )
    return out_dir


if __name__ == "__main__":
    run(force="--force" in sys.argv[1:])
