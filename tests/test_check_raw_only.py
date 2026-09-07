"""tools/check_raw_only.py: der statische Wächter muss die drei Fallen aus
dem Auftrag (zusammengesetzte Pfade, Vertragspfade, Weichen) auf einem
gepflanzten Beispiel erkennen und auf einem sauberen Baum grün laufen.

Wie test_check_hardlink_safety.py arbeitet dies ausschließlich auf einem
temporären Verzeichnis (tempfile) - hängt nicht an echtem Repo-Code, damit
der Test nicht von dessen aktuellem Zustand abhängt.
"""
from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
for p in (str(PROJECT_ROOT), str(TOOLS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from check_raw_only import run_check  # noqa: E402


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")


def test_clean_tree_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root,
            "windkraft/calc/ok.py",
            """
            from pathlib import Path
            from pipeline import contract

            def write_output(grid):
                out = contract.PRODUCTS["abschichtung_tif"]
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"x")

            def read_raw():
                # Lesen aus data/ ist erlaubt, nur Schreiben ist verboten.
                frame = contract.RAW["admin"]["vgd"]
                return frame.exists()
            """,
        )
        result = run_check(root)
        assert result.ok, [f.reason for f in result.findings]
        assert result.files_scanned == 1


def test_detects_compound_path_write():
    """Falle 1: `ROOT / "data" / "x"` enthält keinen Teilstring "data/" -
    eine reine Textsuche fände das nicht, der AST-Wächter muss es finden."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root,
            "windkraft/calc/bad_compound.py",
            """
            from pathlib import Path

            ROOT = Path("/irgendwo")

            def cache_it(frame):
                target = ROOT / "data" / "adressregister" / "cache.parquet"
                frame.to_parquet(target)
            """,
        )
        result = run_check(root)
        assert not result.ok
        assert any(".to_parquet" in f.call_desc for f in result.findings)


def test_detects_contract_raw_write():
    """Falle 2: ein Schreibzugriff auf contract.RAW[...] ist ein
    Schreibzugriff nach data/, auch ohne dass im Code "data" steht."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root,
            "windkraft/calc/bad_contract.py",
            """
            from pipeline import contract

            def overwrite_raw():
                path = contract.RAW["admin"]["vgd"]
                path.write_bytes(b"oops")
            """,
        )
        result = run_check(root)
        assert not result.ok
        assert any(".write_bytes" in f.call_desc for f in result.findings)


def test_detects_default_value_weiche():
    """Falle 3: eine Weiche - ein Vorgabewert, der nur greift, wenn eine
    Datei/ein Verzeichnis fehlt - wie die Cache-Weiche aus W1.1."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root,
            "windkraft/calc/bad_default.py",
            """
            from pipeline.contract import DATA

            def load_address_points(cache_dir=None):
                cache_dir = cache_dir or (DATA / "adressen" / "_cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
            """,
        )
        result = run_check(root)
        assert not result.ok
        assert any(".mkdir" in f.call_desc for f in result.findings)


def test_output_and_build_writes_are_not_flagged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root,
            "pipeline/layers/ok.py",
            """
            from pathlib import Path

            BUILD = Path("/repo/build")

            def write_layer(grid):
                target = BUILD / "layers" / "x.tif"
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "wb") as f:
                    f.write(b"x")
            """,
        )
        result = run_check(root)
        assert result.ok, [f.reason for f in result.findings]


def test_tests_and_docs_dirs_are_out_of_scope():
    """Dokumentierte Lücke: tests/ und docs/ werden nicht gescannt."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root,
            "tests/test_would_violate.py",
            """
            from pathlib import Path
            ROOT = Path("/irgendwo")
            (ROOT / "data" / "x").write_text("egal")
            """,
        )
        result = run_check(root)
        assert result.ok
        assert result.files_scanned == 0
