"""tools/check_hardlink_safety.py: Regel A (output/) und Regel B (data/,
seit W1.3 *jede* Datei, nicht mehr nur deklarierte Schreibziele) müssen
einen echten, gepflanzten Hardlink-Verstoß erkennen und auf einem sauberen
Baum grün laufen.

Arbeitet ausschließlich auf einem temporären Verzeichnis (tempfile) — hängt
nicht an den echten data/-/output/-Bäumen dieses Repos, damit der Test nicht
davon abhängt, was gerade lokal unter data/ oder output/ liegt.

Die Namen im Testbaum sind trotzdem echte: W4.3 hat hier den Rest der
DECLARED-Ära entfernt, der noch `data/adressregister/adressen_31287.parquet`
anlegte — ein Verzeichnis, das W0.1 nach `data/adressen/` umbenannt hat, und
eine Datei, die seit W1.1/W1.P3 unter `build/prep/adressen/` entsteht und
nicht mehr unter `data/`. Der Test lief davon unberührt grün (tempfile), aber
er lehrte jeden Leser einen Pfad, den es nicht mehr gibt. Für Regel B ist der
Name ohnehin gleichgültig — seit W1.3 zählt *jede* Datei unter `data/`, nicht
mehr eine deklarierte Teilmenge bekannter Schreibziele.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
for p in (str(PROJECT_ROOT), str(TOOLS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from check_hardlink_safety import run_check  # noqa: E402


def _make_tree(root: Path) -> None:
    (root / "output" / "noe").mkdir(parents=True)
    (root / "output" / "kataster").mkdir(parents=True)
    (root / "data" / "adressen").mkdir(parents=True)


def test_clean_tree_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)

        # gewöhnliche Ausgaben, Link-Count 1
        (root / "output" / "noe" / "alignment_x.json").write_text("{}")
        (root / "output" / "kataster" / "big.geoparquet").write_text("data")
        # gewöhnliche Datei unter data/, Link-Count 1 — seit W1.3 der
        # Normalfall für jede Datei dort, nicht nur für Schreibziele
        (root / "data" / "adressen" / "ADRESSE.csv").write_text("x")

        result = run_check(root)

        assert result.ok, result.violations
        assert result.checked_a == 2
        assert result.checked_b == 1


def test_detects_planted_hardlink_violation_under_output():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)

        target = root / "output" / "kataster" / "at_dkm.geoparquet"
        target.write_text("payload")
        # Hardlink pflanzen: zweiter Verzeichniseintrag auf denselben Inode
        shared = root / "output" / "kataster" / "at_dkm_shared_with_other_repo.geoparquet"
        os.link(target, shared)

        result = run_check(root)

        assert not result.ok
        violated_paths = {v.path for v in result.violations}
        assert target in violated_paths
        assert shared in violated_paths
        assert all(v.rule == "A" for v in result.violations)
        assert all(v.link_count == 2 for v in result.violations)


def test_detects_planted_hardlink_violation_under_data():
    """Seit W1.3 ist JEDE Datei unter data/ betroffen, nicht mehr nur eine
    deklarierte Teilmenge bekannter Schreibziele."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)

        quelle = root / "data" / "adressen" / "ADRESSE.csv"
        quelle.write_text("roh")
        # simuliert: dieselbe Datei noch per Hardlink mit dem Alt-Repo geteilt
        other_repo_copy = root / "ADRESSE_altes_repo.csv"
        os.link(quelle, other_repo_copy)

        result = run_check(root)

        assert not result.ok
        assert len(result.violations) == 1
        v = result.violations[0]
        assert v.rule == "B"
        assert v.path == quelle
        assert v.link_count == 2


def test_empty_data_dir_is_not_a_violation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        # data/ ist leer bis auf leere Unterverzeichnisse

        result = run_check(root)

        assert result.ok
        assert result.checked_b == 0


def test_missing_output_dir_is_not_a_violation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data").mkdir()
        # output/ existiert absichtlich nicht

        result = run_check(root)

        assert result.ok
        assert result.checked_a == 0
