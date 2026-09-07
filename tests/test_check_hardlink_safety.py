"""tools/check_hardlink_safety.py: Regel A (output/) und Regel B (data/-
Schreibziele) müssen einen echten, gepflanzten Hardlink-Verstoß erkennen und
auf einem sauberen Baum grün laufen.

Arbeitet ausschließlich auf einem temporären Verzeichnis (tempfile) — hängt
nicht an den echten data/-/output/-Bäumen dieses Repos, damit der Test nicht
davon abhängt, was gerade lokal unter data/ oder output/ liegt.
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

DECLARED = ("adressregister/adressen_31287.parquet",)


def _make_tree(root: Path) -> None:
    (root / "output" / "noe").mkdir(parents=True)
    (root / "output" / "kataster").mkdir(parents=True)
    (root / "data" / "adressregister").mkdir(parents=True)


def test_clean_tree_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)

        # gewöhnliche Ausgaben, Link-Count 1
        (root / "output" / "noe" / "alignment_x.json").write_text("{}")
        (root / "output" / "kataster" / "big.geoparquet").write_text("data")
        # deklariertes Schreibziel unter data/, Link-Count 1
        (root / "data" / "adressregister" / "adressen_31287.parquet").write_text("x")
        # gewöhnliches, per Hardlink übernommenes Quellmaterial unter data/ -
        # NICHT in DECLARED, darf Link-Count > 1 haben ohne Verstoß zu sein
        source = root / "data" / "raw_input.zip"
        source.write_text("raw")
        os.link(source, root / "data" / "raw_input_linked.zip")

        result = run_check(root, declared_targets=DECLARED)

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

        result = run_check(root, declared_targets=DECLARED)

        assert not result.ok
        violated_paths = {v.path for v in result.violations}
        assert target in violated_paths
        assert shared in violated_paths
        assert all(v.rule == "A" for v in result.violations)
        assert all(v.link_count == 2 for v in result.violations)


def test_detects_planted_hardlink_violation_under_data_write_target():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)

        cache = root / "data" / "adressregister" / "adressen_31287.parquet"
        cache.write_text("cached")
        # simuliert: derselbe Cache noch per Hardlink mit dem Alt-Repo geteilt
        other_repo_copy = root / "adressen_31287_altes_repo.parquet"
        os.link(cache, other_repo_copy)

        result = run_check(root, declared_targets=DECLARED)

        assert not result.ok
        assert len(result.violations) == 1
        v = result.violations[0]
        assert v.rule == "B"
        assert v.path == cache
        assert v.link_count == 2


def test_missing_declared_target_is_not_a_violation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        # data/adressen/adressen_31287.parquet existiert absichtlich nicht

        result = run_check(root, declared_targets=DECLARED)

        assert result.ok
        assert result.checked_b == 0


def test_missing_output_dir_is_not_a_violation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data").mkdir()
        # output/ existiert absichtlich nicht

        result = run_check(root, declared_targets=())

        assert result.ok
        assert result.checked_a == 0
