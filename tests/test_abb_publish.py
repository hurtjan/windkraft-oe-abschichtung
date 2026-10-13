"""abb_publish mit gemocktem `gh` (subprocess/shutil gepatcht)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.analysis.whitepaper import abb_publish as ap


def cp(rc=0, out=""):
    return subprocess.CompletedProcess([], rc, out, "")


@pytest.fixture
def env(tmp_path, monkeypatch):
    abb = tmp_path / "abb"
    abb.mkdir()
    (abb / "a.png").write_bytes(b"A")
    (abb / "b.svg").write_bytes(b"B")
    monkeypatch.setattr(ap, "ABB_DIR", abb)
    monkeypatch.setattr(ap, "MANIFEST_DIR", tmp_path / "m")
    monkeypatch.setattr(ap, "tif_sha", lambda *a: "abc123def456")
    monkeypatch.setattr(ap, "git_state", lambda: {"commit": "deadbeef", "dirty": True})
    monkeypatch.setattr(ap.shutil, "which", lambda n: "/bin/gh")
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)
        if cmd[:3] == ["gh", "release", "view"]:
            return cp(0, json.dumps({"assets": [{"name": "a.png"}, {"name": "alt.png"}]}))
        return cp()
    monkeypatch.setattr(ap.subprocess, "run", fake)
    return tmp_path, calls


def test_missing_gh(env, monkeypatch, capsys):
    monkeypatch.setattr(ap.shutil, "which", lambda n: None)
    with pytest.raises(SystemExit):
        ap.main([])
    assert "brew install gh" in capsys.readouterr().err


def test_not_logged_in(env, monkeypatch, capsys):
    monkeypatch.setattr(ap.subprocess, "run", lambda c, **k: cp(1))
    with pytest.raises(SystemExit):
        ap.main([])
    assert "gh auth login" in capsys.readouterr().err


def test_no_figures(env, capsys):
    for p in ap.ABB_DIR.iterdir():
        p.unlink()
    with pytest.raises(SystemExit):
        ap.main([])
    assert "keine" in capsys.readouterr().err


def test_dry_run_plan_and_manifest(env, capsys):
    tmp, calls = env
    assert ap.main([]) == 0
    out = capsys.readouterr().out
    assert "alt.png" in out and "Trockenlauf" in out
    assert "releases/download/abbildungen-latest/a.png" in out
    assert not any(c[2] in ("edit", "create", "upload", "delete-asset") for c in calls if c[:2] == ["gh", "release"])
    m = json.loads((tmp / "m" / "manifest.json").read_text())
    assert m["tif_sha256"] == "abc123def456" and m["git"]["dirty"] is True
    assert {f["name"] for f in m["files"]} == {"a.png", "b.svg"}
    assert all(len(f["sha256"]) == 64 for f in m["files"])


def test_confirm_executes(env):
    _, calls = env
    ap.main(["--confirm"])
    verbs = [c[2] for c in calls if c[:2] == ["gh", "release"]]
    assert verbs == ["view", "edit", "upload", "delete-asset"]
