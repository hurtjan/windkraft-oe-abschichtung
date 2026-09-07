"""pipeline/fingerprint.py: der Fingerabdruck-Mechanismus aus Entscheidung
(c) (docs/rewrite/PLAN.md §5) - vorbereitet von Paket W1.P0 (§13.4), damit
nicht jedes der neun Prep-Pakete seine eigene, leicht andere Logik
erfindet (siehe Modul-Docstring von pipeline/fingerprint.py)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import fingerprint  # noqa: E402


def _make_input(tmp_path: Path, name: str, content: str = "x") -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_write_then_matches_true(tmp_path):
    inputs = [_make_input(tmp_path, "a.txt"), _make_input(tmp_path, "b.txt")]
    prep_dir = tmp_path / "prep_out"
    fp_path = fingerprint.write(prep_dir, inputs)

    assert fp_path == prep_dir / fingerprint.FINGERPRINT_FILENAME
    assert fp_path.exists()
    assert fingerprint.matches(prep_dir, inputs)


def test_write_creates_prep_dir(tmp_path):
    inputs = [_make_input(tmp_path, "a.txt")]
    prep_dir = tmp_path / "does" / "not" / "exist" / "yet"
    assert not prep_dir.exists()

    fingerprint.write(prep_dir, inputs)

    assert prep_dir.is_dir()


def test_matches_false_without_fingerprint(tmp_path):
    inputs = [_make_input(tmp_path, "a.txt")]
    prep_dir = tmp_path / "prep_out"
    prep_dir.mkdir()

    assert not fingerprint.matches(prep_dir, inputs)


def test_matches_false_after_input_changes(tmp_path):
    a = _make_input(tmp_path, "a.txt")
    prep_dir = tmp_path / "prep_out"
    fingerprint.write(prep_dir, [a])
    assert fingerprint.matches(prep_dir, [a])

    # Inhalt UND Größe ändern - stellt sicher, dass die Änderung sich in
    # Größe oder mtime niederschlägt, unabhängig von Dateisystem-Auflösung.
    time.sleep(0.01)
    a.write_text("ein ganz anderer, laengerer Inhalt", encoding="utf-8")

    assert not fingerprint.matches(prep_dir, [a])


def test_matches_false_when_input_set_changes(tmp_path):
    a = _make_input(tmp_path, "a.txt")
    b = _make_input(tmp_path, "b.txt")
    prep_dir = tmp_path / "prep_out"
    fingerprint.write(prep_dir, [a])

    assert not fingerprint.matches(prep_dir, [a, b])


def test_matches_false_on_corrupt_fingerprint_file(tmp_path):
    inputs = [_make_input(tmp_path, "a.txt")]
    prep_dir = tmp_path / "prep_out"
    prep_dir.mkdir()
    (prep_dir / fingerprint.FINGERPRINT_FILENAME).write_text("kein json{{{", encoding="utf-8")

    assert not fingerprint.matches(prep_dir, inputs)


def test_compute_keys_are_full_paths_not_just_names(tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    same_name_a = _make_input(d1, "same.txt", "aus d1")
    same_name_b = _make_input(d2, "same.txt", "aus d2")

    result = fingerprint.compute([same_name_a, same_name_b])

    assert set(result.keys()) == {str(same_name_a), str(same_name_b)}
