#!/usr/bin/env python3
"""Prüft mechanisch die Hardlink-Invariante dieses Repos.

Invariante: Jede Datei, die irgendein Codepfad schreiben kann, ist eine
echte Kopie — nie ein Hardlink. Unabhängig von Größe, Verzeichnis und davon,
ob im Code ein Overwrite-Schutz existiert.

Das ergibt zwei Regeln, keine Klassifikation:

  Regel A: Keine Datei unter output/ darf einen Link-Count > 1 haben.
           Ausgaben werden nie geteilt, ohne Ausnahme — alles unter output/
           kann von der Kette geschrieben werden, und "aktuell schreibt sie
           nichts dorthin" ist keine verlässliche Garantie für die Zukunft.

  Regel B: Eine explizit deklarierte Liste bekannter Schreibziele unter
           data/ (siehe DECLARED_DATA_WRITE_TARGETS unten) muss Link-Count 1
           haben. data/ ist überwiegend echtes, per Hardlink übernommenes
           Quellmaterial (rein lesend, das ist korrekt und bleibt so) — bis
           auf diese benannten Ausnahmen, die die Kette selbst beschreibt.

Warum zwei Regeln statt einer Klassifikation "Eingaben hardlinken, Ausgaben
kopieren": genau diese Klassifikation hat vorher versagt. Die Adressregister-
Caches und die output/noe-/output/kataster-Dateien wurden korrekt als
"Artefakte, die (auch) gelesen werden" eingeordnet — und trotzdem schreibt
die Kette in sie hinein. Eine Regel, die bei einer korrekten Einordnung
trotzdem falsch liegt, ist die falsche Regel. Der Link-Count ist ein
Tatsache, keine Einordnung; er lässt sich nicht falsch einschätzen.

Exit-Code 0, wenn keine Verstöße gefunden wurden; ungleich 0 sonst.
Keine externen Abhängigkeiten, kein Zugriff auf das Alt-Repo, läuft in
Sekunden (nur stat(), kein Lesen von Dateiinhalten).
"""
from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Regel B — bekannte Schreibziele unter data/.
#
# Das ist die einzige Stelle, die bei einem neuen Schreibziel unter data/
# angefasst werden muss: einen Pfad (relativ zu data/) hier ergänzen, fertig.
# Aktuell die beiden Adressregister-Parquet-Caches, die
# windkraft/calc/bev_register.py per to_parquet() anlegt (siehe
# docs/FOLLOWUPS.md, Abschnitt zur Datenmigration per Hardlink).
# ---------------------------------------------------------------------------
DECLARED_DATA_WRITE_TARGETS: tuple[str, ...] = (
    "adressen/adressen_31287.parquet",
    "adressen/bev_gebaeude_31287.parquet",
)


@dataclass(frozen=True)
class Violation:
    rule: str  # "A" oder "B"
    path: Path
    inode: int
    link_count: int


def _stat_if_real_file(path: Path) -> os.stat_result | None:
    """lstat() auf `path`, oder None wenn es kein reguläres File ist.

    lstat() statt stat(): Symlinks selbst sollen nicht als "Hardlink" zählen
    (ihr Link-Count betrifft den Symlink-Inode, nicht das Ziel).
    """
    try:
        st = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    return st


def check_rule_a(output_dir: Path) -> tuple[list[Violation], int]:
    """Regel A: kein File unter `output_dir` darf Link-Count > 1 haben.

    Gibt (Verstöße, Anzahl geprüfter Dateien) zurück. Ein nicht existierender
    `output_dir` ist kein Fehler (0 geprüft, 0 Verstöße) — z. B. vor dem
    ersten Kettenlauf.
    """
    violations: list[Violation] = []
    checked = 0
    if not output_dir.exists():
        return violations, checked
    for dirpath, _dirnames, filenames in os.walk(output_dir):
        for name in filenames:
            path = Path(dirpath) / name
            st = _stat_if_real_file(path)
            if st is None:
                continue
            checked += 1
            if st.st_nlink > 1:
                violations.append(Violation("A", path, st.st_ino, st.st_nlink))
    return violations, checked


def check_rule_b(
    data_dir: Path, declared_targets: tuple[str, ...] = DECLARED_DATA_WRITE_TARGETS
) -> tuple[list[Violation], int]:
    """Regel B: die deklarierten Schreibziele unter `data_dir` müssen
    Link-Count 1 haben.

    Ein deklariertes Ziel, das (noch) nicht existiert, ist kein Verstoß —
    es ist schlicht noch nicht angelegt. Gibt (Verstöße, Anzahl tatsächlich
    vorhandener und geprüfter Ziele) zurück.
    """
    violations: list[Violation] = []
    checked = 0
    for rel in declared_targets:
        path = data_dir / rel
        st = _stat_if_real_file(path)
        if st is None:
            continue
        checked += 1
        if st.st_nlink > 1:
            violations.append(Violation("B", path, st.st_ino, st.st_nlink))
    return violations, checked


@dataclass(frozen=True)
class CheckResult:
    violations: list[Violation]
    checked_a: int
    checked_b: int

    @property
    def checked_total(self) -> int:
        return self.checked_a + self.checked_b

    @property
    def ok(self) -> bool:
        return not self.violations


def run_check(
    repo_root: Path, declared_targets: tuple[str, ...] = DECLARED_DATA_WRITE_TARGETS
) -> CheckResult:
    violations_a, checked_a = check_rule_a(repo_root / "output")
    violations_b, checked_b = check_rule_b(repo_root / "data", declared_targets)
    return CheckResult(violations_a + violations_b, checked_a, checked_b)


def format_report(result: CheckResult) -> str:
    lines: list[str] = []
    for v in result.violations:
        regel = "Regel A (output/)" if v.rule == "A" else "Regel B (data/-Schreibziel)"
        lines.append(
            f"VERSTOSS [{regel}]: {v.path}  "
            f"(Inode {v.inode}, Link-Count {v.link_count}, erwartet 1)"
        )
    if result.ok:
        lines.append(
            f"OK: {result.checked_total} Dateien geprüft "
            f"({result.checked_a} unter output/, {result.checked_b} deklarierte "
            f"Schreibziele unter data/) — keine Hardlink-Verstöße gefunden."
        )
    else:
        lines.append(
            f"FEHLGESCHLAGEN: {len(result.violations)} von {result.checked_total} "
            f"geprüften Dateien verstoßen gegen die Hardlink-Invariante."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    result = run_check(REPO_ROOT)
    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
