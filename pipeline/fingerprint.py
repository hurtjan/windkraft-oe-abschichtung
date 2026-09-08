"""Fingerabdruck der Eingänge einer Stufe (Entscheidung (c), docs/rewrite/PLAN.md §5).

Jede Prep-Stufe (W1.P1-W1.P9) schreibt nach einem erfolgreichen Lauf einen
Fingerabdruck ihrer tatsächlich gelesenen Eingaben. Ein späterer Aufrufer -
ein erneuter Prep-Lauf oder, laut Nebenbefund in PLAN.md §12, auch die
Layer-Stufe (W2.1-W2.3) - prüft mit ``matches()``, ob sich seither eine der
Eingaben geändert hat, und kann dann hart abbrechen statt mit veralteten
Zwischenständen weiterzurechnen.

Dieses Modul liegt bewusst auf Höhe von ``pipeline/contract.py`` und
``pipeline/runtime.py`` - nicht unter ``pipeline/prep/`` - weil laut
PLAN.md §12 ("Nebenbefund mit Folgen für Welle 2") *derselbe* Mechanismus
auch von der Layer-Stufe gebraucht wird, die keine Prep-Stufe ist. Ohne
dieses Vorpaket hätte vermutlich jedes der neun Prep-Pakete seine eigene,
leicht andere Fingerabdruck-Logik erfunden - genau die Inkonsistenz, vor
der der Nebenbefund warnt. Kein Paket aus §7 "besitzt" diese Datei; sie ist
Infrastruktur wie ``pipeline/runtime.py`` (siehe dessen Docstring).

Größe und Änderungszeit (nicht der Dateiinhalt) bilden den Fingerabdruck -
ein Hash über mehrere GB Rohdaten bei jedem Lauf wäre selbst die Kosten,
die die Prep-Stufe laut Entscheidung (c) gerade vermeiden soll ("läuft
nicht bei jedem Kettenlauf mit").
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline import contract

FINGERPRINT_FILENAME = ".fingerprint.json"


def _stat(path: Path) -> dict:
    st = path.stat()
    return {"size": st.st_size, "mtime_ns": st.st_mtime_ns}


def compute(inputs: list[Path]) -> dict:
    """Baut den Fingerabdruck-Datensatz für die gegebenen Eingaben.

    Schlüssel ist der Pfad als String, **relativ zu ``contract.ROOT``**, wenn
    die Eingabe innerhalb des Repos liegt - nicht der volle absolute Pfad
    (W6.4, docs/rewrite/FORTSCHRITT.md Punkt 53): der volle Pfad hängt am
    Klonort, ``contract.ROOT`` selbst leitet sich aus ``__file__`` ab, also
    hätte jeder Klon andere Schlüssel und nie einen Treffer - auch wenn die
    Dateien (z. B. über einen read-only-Symlink wie ``derived/prep/`` in
    ``make worktree``) buchstäblich dieselben sind. Für alles außerhalb von
    ``contract.ROOT`` (kann laut Vertrag nicht vorkommen, aber ``compute()``
    prüft das nicht) bleibt der Rückfall der aufgelöste absolute Pfad -
    weiterhin voll, nicht nur der Dateiname: zwei gleichnamige Dateien aus
    verschiedenen Verzeichnissen (z. B. je ein Bundesland-ZIP) dürfen sich
    nicht überschreiben.
    """
    result = {}
    for p in inputs:
        try:
            key = str(p.relative_to(contract.ROOT))
        except ValueError:
            key = str(p.resolve())
        result[key] = _stat(p)
    return result


def write(prep_dir: Path, inputs: list[Path]) -> Path:
    """Schreibt den Fingerabdruck der gegebenen Eingaben nach
    ``<prep_dir>/.fingerprint.json`` und gibt den geschriebenen Pfad zurück.

    Legt ``prep_dir`` an, falls es noch nicht existiert (wie
    ``pipeline.runtime.ensure_dir`` - kein eigener mkdir-Aufruf nötig).
    """
    prep_dir.mkdir(parents=True, exist_ok=True)
    fp_path = prep_dir / FINGERPRINT_FILENAME
    fp_path.write_text(
        json.dumps(compute(inputs), indent=2, sort_keys=True), encoding="utf-8"
    )
    return fp_path


def matches(prep_dir: Path, inputs: list[Path]) -> bool:
    """True, wenn der unter ``prep_dir`` gespeicherte Fingerabdruck exakt zu
    den aktuellen ``inputs`` passt.

    False, wenn die Fingerabdruckdatei fehlt, nicht lesbar ist, oder sich
    Größe/Änderungszeit einer Eingabe geändert haben - auch dann, wenn sich
    nur die Menge der Eingaben selbst geändert hat (eine hinzugekommene
    oder weggefallene Datei zählt als Änderung).
    """
    fp_path = prep_dir / FINGERPRINT_FILENAME
    if not fp_path.exists():
        return False
    try:
        stored = json.loads(fp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return stored == compute(inputs)
