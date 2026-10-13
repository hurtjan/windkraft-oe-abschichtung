"""Abbildungen als Assets eines festen GitHub-Releases veroeffentlichen.

Standard ist ein Trockenlauf; nur mit --confirm werden `gh`-Befehle mit
Schreibwirkung ausgefuehrt. Ein Release (`abbildungen-latest`), Assets werden
ueberschrieben, Verlauf gibt es nicht.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "hurtjan/windkraft-oe-abschichtung"
TAG = "abbildungen-latest"
TITLE = "Abbildungen (aktuell)"
ROOT = Path(__file__).resolve().parents[3]
ABB_DIR = ROOT / "docs" / "whitepaper" / "abb"
ZAHLEN = ROOT / "docs" / "whitepaper" / "tabellen" / "zahlen.json"
MANIFEST_DIR = ROOT / "derived" / "work" / "whitepaper"
MANIFEST_NAME = "manifest.json"


def fail(msg: str) -> None:
    print(f"Abbruch: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def check_gh() -> None:
    if shutil.which("gh") is None:
        fail("`gh` (GitHub CLI) wurde nicht gefunden. Installieren mit: brew install gh")
    if _run(["gh", "auth", "status"]).returncode != 0:
        fail("`gh` ist nicht angemeldet. Anmelden mit: gh auth login")


def local_files(abb_dir: Path | None = None) -> list[Path]:
    abb_dir = abb_dir or ABB_DIR
    files = sorted(p for p in abb_dir.glob("*") if p.suffix in (".png", ".svg") and p.is_file())
    if not files:
        fail(f"In {abb_dir} liegen keine *.png/*.svg. Zuerst `make whitepaper` ausfuehren.")
    return files


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tif_sha(zahlen: Path = ZAHLEN) -> str | None:
    """TIF-Stand (sha256-Kurzform, 12 Zeichen) aus der Zahlenregistry (haeufigster Wert)."""
    try:
        data = json.loads(zahlen.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    c = collections.Counter(v["stand"] for v in data.values()
                            if isinstance(v, dict) and v.get("stand"))
    return c.most_common(1)[0][0] if c else None


def git_state() -> dict:
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip() or None
    dirty = bool(_run(["git", "status", "--porcelain"]).stdout.strip())
    return {"commit": head, "dirty": dirty}


def build_manifest(files: list[Path]) -> dict:
    return {
        "repo": REPO, "release": TAG,
        "tif_sha256": tif_sha(),
        "git": git_state(),
        "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": [{"name": p.name, "sha256": sha256(p)} for p in files],
    }


def release_assets() -> tuple[bool, set[str]]:
    r = _run(["gh", "release", "view", TAG, "--repo", REPO, "--json", "assets"])
    if r.returncode != 0:
        return False, set()
    try:
        return True, {a["name"] for a in json.loads(r.stdout).get("assets", [])}
    except ValueError:
        return True, set()


def notes(m: dict) -> str:
    g = m["git"]
    return (f"Automatisch erzeugte Abbildungen (werden bei jeder Veroeffentlichung ueberschrieben). "
            f"TIF sha256 {m['tif_sha256'] or 'unbekannt'}, Commit {g['commit']}"
            f"{' (dirty)' if g['dirty'] else ''}, Stand {m['timestamp']}.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="wirklich veroeffentlichen")
    args = ap.parse_args(argv)

    check_gh()
    files = local_files()
    manifest = build_manifest(files)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    mpath = MANIFEST_DIR / MANIFEST_NAME
    mpath.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")

    exists, remote = release_assets()
    names = {p.name for p in files} | {MANIFEST_NAME}
    stale = sorted(remote - names)
    paths = [str(p) for p in files] + [str(mpath)]
    text = notes(manifest)
    cmds: list[list[str]] = []
    if exists:
        cmds.append(["gh", "release", "edit", TAG, "--repo", REPO, "--notes", text])
    else:
        cmds.append(["gh", "release", "create", TAG, "--repo", REPO, "--title", TITLE,
                     "--notes", text, "--prerelease", "--latest=false"])
    cmds.append(["gh", "release", "upload", TAG, *paths, "--repo", REPO, "--clobber"])
    cmds += [["gh", "release", "delete-asset", TAG, n, "-y", "--repo", REPO] for n in stale]

    print(f"Release {TAG}: {'vorhanden' if exists else 'fehlt (wird angelegt)'}")
    print(f"Hochladen: {len(files)} Abbildungen + {MANIFEST_NAME}")
    print(f"Veraltete Remote-Assets (loeschen): {', '.join(stale) or 'keine'}")
    print(f"TIF sha256: {manifest['tif_sha256']}  Commit: {manifest['git']['commit']}"
          f"{' (dirty)' if manifest['git']['dirty'] else ''}")
    print("Befehle:")
    for c in cmds:
        print("  " + " ".join(c[:8]) + (" ..." if len(c) > 8 else ""))

    if not args.confirm:
        print("\nTrockenlauf, nichts veroeffentlicht. Mit `make abb-publish CONFIRM=1` ausfuehren.")
    else:
        for c in cmds:
            r = subprocess.run(c, cwd=ROOT)
            if r.returncode != 0:
                fail(f"Befehl fehlgeschlagen: {' '.join(c[:5])}")
        print("\nVeroeffentlicht.")
    base = f"https://github.com/{REPO}/releases/download/{TAG}"
    print("URLs:")
    for n in sorted(names):
        print(f"  {base}/{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
