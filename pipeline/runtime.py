"""Erzeugt derived/- und out/-Verzeichnisse bei Bedarf.

``pipeline/contract.py`` beschreibt nur - kein Dateizugriff, kein ``mkdir``
beim Import (siehe dessen Modul-Docstring). Das Anlegen der Verzeichnisse
gehört deshalb hierher: eine Nebenwirkung, aber eine, die niemand ungewollt
auslöst, weil dieses Modul nur beim tatsächlichen Schreiben importiert wird.

Aufrufer (Prep-, Layer- und Finalize-Stufen ab Welle 1) rufen ``ensure_dir``
bzw. ``ensure_parent`` für jeden Pfad, in den sie tatsächlich schreiben -
nicht pauschal für den ganzen Baum. Heute (W0.3) hat noch niemand einen
Schreibzugriff auf ``derived/`` oder ``out/``; dieses Modul legt nur die
Grundlage, die die späteren Pakete nutzen.
"""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Legt ``path`` (inkl. Eltern) an, falls es ihn noch nicht gibt.

    Gibt ``path`` unverändert zurück, damit der Aufruf sich in einen
    Ausdruck einfügen lässt.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent(file_path: Path) -> Path:
    """Legt das Elternverzeichnis von ``file_path`` an, falls nötig.

    Gibt ``file_path`` unverändert zurück - gedacht für den unmittelbaren
    Aufruf vor dem Öffnen einer Datei zum Schreiben, etwa
    ``open(ensure_parent(contract.PRODUCTS["abschichtung_tif"]), "wb")``.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path
