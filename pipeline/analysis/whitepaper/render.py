"""Rendert ``paper_vorlage.md`` zu ``paper.md`` (Platzhalter -> Registerwerte).

Platzhalter:
  ``{{z:KEY}}``        Zahl aus dem Register (zahlen.json), deutsch formatiert
  ``{{z:KEY|0}}``      mit 0 Nachkommastellen (Dezimalkomma)
  ``{{z:KEY|%1}}``     Prozent mit 1 Nachkommastelle, "12,3 %"
  ``{{tab:NAME}}``     Inhalt von tabellen/NAME.md (Tabelle + Legende)
Tausendertrenner: einfaches Leerzeichen (wie im bisherigen Text).
Unbekannte Schluessel/Tabellen sind harte Fehler.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

PLATZHALTER = re.compile(r"\{\{\s*(z|tab)\s*:\s*([A-Za-z0-9_.]+)\s*(?:\|\s*(%?)(\d+))?\s*\}\}")
KOPF = ("<!-- GENERIERT aus paper_vorlage.md durch make whitepaper — nicht von Hand ändern. "
        "Stand: {datum}, TIF {sha} -->")


class RenderError(RuntimeError):
    pass


def format_de(x: float | int, decimals: int | None = None, percent: bool = False) -> str:
    """Deutsche Zahl: Leerzeichen als Tausendertrenner, Komma als Dezimalzeichen."""
    if decimals is None:
        decimals = 0 if (isinstance(x, int) or float(x).is_integer()) else 1
    sign = "-" if round(abs(float(x)), decimals) != 0 and x < 0 else ""
    s = f"{abs(float(x)):,.{decimals}f}"
    ip, _, frac = s.partition(".")
    ip = ip.replace(",", " ")
    out = f"{sign}{ip},{frac}" if decimals else f"{sign}{ip}"
    return out + " %" if percent else out


def _ohne_titel(text: str) -> str:
    """Entfernt die fuehrende Markdown-Ueberschrift der Tabellendatei samt Leerzeile danach."""
    lines = text.strip("\n").split("\n")
    if lines and re.match(r"#{1,6}\s", lines[0]):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines)


def render(vorlage: str, zahlen: dict[str, dict], tabellen_dir: Path,
           datum: str | None = None, sha: str = "?") -> tuple[str, set[str]]:
    """Gibt (gerenderter Text, benutzte Schluessel) zurueck. Fehler: RenderError."""
    used: set[str] = set()
    fehlt_z: list[str] = []
    fehlt_t: list[str] = []

    def repl(m: re.Match) -> str:
        kind, name, pct, dec = m.groups()
        if kind == "z":
            if name not in zahlen:
                fehlt_z.append(name)
                return m.group(0)
            used.add(name)
            return format_de(zahlen[name]["wert"], int(dec) if dec is not None else None, percent=bool(pct))
        p = Path(tabellen_dir) / f"{name}.md"
        if not p.is_file():
            fehlt_t.append(name)
            return m.group(0)
        return _ohne_titel(p.read_text(encoding="utf-8"))

    body = PLATZHALTER.sub(repl, vorlage)
    if fehlt_z or fehlt_t:
        msg = []
        if fehlt_z:
            msg.append("Unbekannte Registerschluessel: " + ", ".join(sorted(set(fehlt_z))))
        if fehlt_t:
            msg.append("Unbekannte Tabellen: " + ", ".join(sorted(set(fehlt_t))))
        raise RenderError("; ".join(msg))
    rest = re.findall(r"\{\{.*?\}\}", body)
    if rest:
        raise RenderError(f"Nicht aufloesbare Platzhalter: {sorted(set(rest))}")
    kopf = KOPF.format(datum=datum or date.today().isoformat(), sha=sha)
    return kopf + "\n" + body, used


def run(vorlage_path: Path, paper_path: Path, zahlen: dict[str, dict], tabellen_dir: Path,
        sha: str, datum: str | None = None) -> set[str]:
    vorlage_path = Path(vorlage_path)
    if not vorlage_path.is_file():
        raise SystemExit(f"[render] Vorlage fehlt: {vorlage_path} (Quelle des White Papers).")
    text, used = render(vorlage_path.read_text(encoding="utf-8"), zahlen, tabellen_dir, datum, sha)
    Path(paper_path).write_text(text, encoding="utf-8")
    unused = sorted(set(zahlen) - used)
    print(f"[render] {paper_path}: {len(used)} Registerschluessel verwendet, {len(unused)} unbenutzt")
    if unused:
        if len(unused) <= 60:
            print("[render] unbenutzte Schluessel: " + ", ".join(unused))
        else:
            groups: dict[str, int] = {}
            for k in unused:
                groups[k.split("_")[0]] = groups.get(k.split("_")[0], 0) + 1
            print("[render] unbenutzte Schluessel nach Praefix: "
                  + ", ".join(f"{p}_*: {n}" for p, n in sorted(groups.items())))
            print("[render] (vollstaendig: Schluessel in zahlen.json abzueglich Platzhalter in paper_vorlage.md)")
    return used
