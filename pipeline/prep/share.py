"""Weitergabe ohne Rohdaten: Prep-Schritt überspringen, wenn das Produkt da ist.

Wird ein Paket mit ``derived/prep`` (aber ohne ``data/``) weitergegeben,
müssen die Prep-Schritte nicht laufen. ``skip_without_raw`` beantwortet das
am Anfang jedes Prep-Runners:

* Rohdaten vorhanden -> ``False``, das bisherige Verhalten (Fingerabdruck,
  Neuberechnung) bleibt unverändert.
* Rohdaten fehlen, Produkte vorhanden -> Hinweis, ``True`` (überspringen).
* Rohdaten fehlen und Produkte fehlen -> klarer Fehler mit Download-Hinweis.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pipeline import contract


def skip_without_raw(
    domain: str,
    raw_inputs: Iterable[Path],
    products: Iterable[Path] | None = None,
    hint: str = "",
    alt_products: Iterable[Path] | None = None,
) -> bool:
    """True = Schritt überspringen (Produkt da, Rohdaten fehlen).

    ``products`` Default: alle ``contract.PREP_FILES[domain]``.
    ``alt_products``: Produkte, die den Schritt ebenfalls überflüssig machen
    (z. B. das kleine Streusiedlungs-Produkt statt des großen Katasters).
    """
    raw_missing = [Path(p) for p in raw_inputs if not Path(p).exists()]
    if not raw_missing:
        return False
    need = list(products) if products is not None else list(contract.PREP_FILES[domain].values())
    if all(p.exists() for p in need):
        print(f"[skip]  prep-{domain}: Produkt vorhanden, Rohdaten fehlen – übersprungen", flush=True)
        return True
    if alt_products is not None:
        alt = list(alt_products)
        if alt and all(p.exists() for p in alt):
            print(
                f"[skip]  prep-{domain}: Rohdaten fehlen, Folgeprodukt vorhanden – übersprungen",
                flush=True,
            )
            return True
    fehlend = [p for p in need if not p.exists()]
    raise SystemExit(
        f"[fehler] prep-{domain}: Produkt fehlt ({', '.join(str(p) for p in fehlend)}) "
        f"und die Rohdaten fehlen ({', '.join(str(p) for p in raw_missing)}). "
        f"Bitte herunterladen/ablegen: {hint or 'siehe docs/rohdaten.md'} (docs/rohdaten.md)."
    )
