"""Zahlenregister des White Papers: ``docs/whitepaper/tabellen/zahlen.json``.

Jeder Analyseschritt traegt seine Zahlen per ``register()`` ein; am Ende des
Laufs schreibt ``write()`` sie (gemergt mit dem bisherigen Stand) als JSON::

    {"schluessel": {"wert": 123.4, "einheit": "km²", "quelle": "...", "stand": "<TIF sha12>"}}

Der Renderer (``render.py``) liest ausschliesslich dieses Register. Keine
handgetippten Ergebniszahlen.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

_REG: dict[str, dict] = {}
_KEY_RE = re.compile(r"^[a-z0-9_.]+$")


def reset() -> None:
    _REG.clear()


def current() -> dict[str, dict]:
    return _REG


def register(key: str, wert: float | int, einheit: str, quelle: str) -> None:
    """Traegt einen Wert ein. Doppelte Schluessel mit anderem Wert sind ein Fehler."""
    if not _KEY_RE.match(key):
        raise ValueError(f"Ungueltiger Registerschluessel {key!r} (erlaubt: a-z, 0-9, _ und . als Namensraum-Trenner).")
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        raise TypeError(f"{key}: Wert muss Zahl sein, ist {type(wert).__name__}.")
    if isinstance(wert, float) and math.isnan(wert):
        return  # nicht definierte Werte (z. B. Anteil an Flaeche 0) nicht registrieren
    entry = {"wert": wert, "einheit": einheit, "quelle": quelle}
    old = _REG.get(key)
    if old is not None and old["wert"] != wert:
        raise ValueError(f"Schluessel {key!r} doppelt mit verschiedenem Wert: {old['wert']} vs {wert}.")
    _REG[key] = entry


def slug(text: str) -> str:
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("≥", "ge"), ("<", "lt"), ("%", " pct "), ("²", "2")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def load(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def merge(old: dict[str, dict], new: dict[str, dict], stand: str) -> dict[str, dict]:
    out = dict(old)
    for k, v in new.items():
        out[k] = {**v, "stand": stand}
    return out


def write(path: Path, stand: str) -> dict[str, dict]:
    """Merged das Register des Laufs in die JSON-Datei (sortiert) und schreibt sie."""
    path = Path(path)
    merged = merge(load(path), _REG, stand)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(merged.items())), ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return merged
