#!/usr/bin/env python3
"""Wegwerf-Verifikationsskript für Paket W0.1b (Pfade nachziehen).

Nicht Teil des Repos. Prüft:
1. config.json: jeder Wert im paths-Block auf Existenz.
2. Jede genannte Codestelle mit funktionalem Pfad: den dort default-mäßig
   gesetzten Pfad einlesen und auf Existenz prüfen.
3. Repo-weite Suche (ohne .git/, docs/, scratchpad) nach alten Verzeichnis-/
   Dateinamen.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/jhurt/Documents/master_windkraft/abschichtung")

print("=" * 70)
print("1) config.json paths-Block")
print("=" * 70)
cfg = json.loads((ROOT / "config.json").read_text())
paths = cfg["paths"]
for key, val in paths.items():
    if key.startswith("_comment") or key in ("nsg_gpkg", "output_dir", "nsg_layers") or not isinstance(val, str):
        print(f"  [skip, kein data/-Pfad] {key} = {val!r}")
        continue
    p = ROOT / val
    exists = p.exists()
    print(f"  {'OK ' if exists else 'FEHLT'} {key:20s} -> {val}  (exists={exists})")

print()
print("=" * 70)
print("2) Funktionale Codestellen (Default-Pfade)")
print("=" * 70)

# (Datei, Beschreibung, Pfad relativ zu ROOT)
checks = [
    ("config.json:vgd", paths["vgd"]),
    ("config.json:osm_dir (Sonderfall - erwartet FEHLT)", paths["osm_dir"]),
    ("config.json:wind_pd_150", paths["wind_pd_150"]),
    ("config.json:wind_pd_100 (Sonderfall - erwartet FEHLT)", paths["wind_pd_100"]),
    ("config.json:dgm", paths["dgm"]),
    ("config.json:nsg_zip", paths["nsg_zip"]),
    ("config.json:powerlines_gpkg (unveraendert)", paths["powerlines_gpkg"]),
    ("wind_zones.py:WK_Eignungszonen (Bgld Positiv)", "data/zonen/WK_Eignungszonen.zip"),
    ("wind_zones.py:RED_III (Ktn)", "data/zonen/RED_III_Windkraftbeschleunigungszone.zip"),
    ("wind_zones.py:WINDKRAFT_AUSSCHLUSSZONE (unveraendert)", "data/WINDKRAFT_AUSSCHLUSSZONE.zip"),
    ("wind_zones.py:WK_Eignungszonen (Bgld Ausschluss)", "data/zonen/WK_Eignungszonen.zip"),
    ("create_noe_dkm_polygon_fill_map.py:ZIP_PATH (kataster, unveraendert)", "data/kataster/KAT_DKM_Niederoesterreich_DXF_20230401.zip"),
    ("create_noe_dkm_polygon_fill_map.py:SYMBOL_CSV (kataster, unveraendert)", "data/kataster/BEV_DKM_DXF_Symbole_V2.6.csv"),
    ("create_noe_dkm_polygon_fill_map.py:ADMIN_BOUNDARY_PATH", "data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp"),
    ("04_create_distance_zones.py:--official-zoning-geojson default", "data/zonen/zonierung_noe.json"),
    ("04_create_distance_zones.py:--vorrangzonen-dir default", "data/zonen/luca_zonen"),
    ("04_create_distance_zones.py:--osm-pbf default", "data/osm/austria-260330.osm.pbf"),
    ("export_at_dkm_geoparquet.py:DEFAULT_SYMBOL_CSV (kataster, unveraendert)", "data/kataster/BEV_DKM_DXF_Symbole_V2.6.csv"),
    ("export_at_dkm_geoparquet.py:DEFAULT_NOE_DXF_ZIP (kataster, unveraendert)", "data/kataster/KAT_DKM_Niederoesterreich_DXF_20230401.zip"),
    ("export_at_dkm_geoparquet.py:--data-dir default (kataster, unveraendert)", "data/kataster"),
    ("extract_noe_vector_layers.py:PDF_PATH", "data/noe_sekrop/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf"),
    ("extract_noe_vector_layers.py:VGD_PATH", "data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp"),
    ("pdf_align.py:_PDF_PATH_MINDESTABSTAND_DEFAULT", "data/noe_sekrop/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf"),
    ("03_build_osm_layers.py:--osm-pbf default", "data/osm/austria-260330.osm.pbf"),
    ("02_build_hig_sources.py:--address-dir default", "data/adressen"),
    ("align_pdf_shapefile.py:VGD", "data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp"),
    ("align_pdf_shapefile.py:PDF_PATH", "data/noe_sekrop/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf"),
    # widmung_sources.py DATASETS (via WIDMUNG root)
    ("widmung_sources.py:bgld", "data/widmung/burgenland/WIDMUNGSFLAECHEN.zip"),
    ("widmung_sources.py:ktn", "data/widmung/kaernten/flawi_ktn_gpkg.zip"),
    ("widmung_sources.py:noe", "data/widmung/niederoesterreich/RRU_WI_HUELLE.gpkg"),
    ("widmung_sources.py:ooe", "data/widmung/oberoesterreich/FLWI_WIDMUNGEN_F.zip"),
    ("widmung_sources.py:sbg", "data/widmung/salzburg/Flaechenwidmung_Shapefile.zip"),
    ("widmung_sources.py:stmk_bauland", "data/widmung/steiermark/Bauland.zip"),
    ("widmung_sources.py:stmk_flaewi", "data/widmung/steiermark/Flaewi.shp.zip"),
    ("widmung_sources.py:tir (glob-Basis)", "data/widmung/tirol"),
    ("widmung_sources.py:vbg", "data/widmung/vorarlberg/fwp_flaeche.gpkg"),
    ("widmung_sources.py:wien", "data/widmung/wien/genflwidmung_wien.geojson"),
]

for label, relpath in checks:
    p = ROOT / relpath
    exists = p.exists()
    print(f"  {'OK ' if exists else 'FEHLT'} {label:60s} -> {relpath}")

print()
print("=" * 70)
print("2b) widmung_sources.py tatsaechlich importieren und _read_raw pruefen")
print("=" * 70)
import sys
sys.path.insert(0, str(ROOT))
try:
    from windkraft.calc import widmung_sources as ws
    print(f"  WIDMUNG root = {ws.WIDMUNG}")
    for key in ws.DATASETS:
        if key == "ktn":
            p = ws.WIDMUNG / "kaernten" / "flawi_ktn_gpkg.zip"
        elif key == "tir":
            try:
                p = ws._tirol_gpkg()
            except FileNotFoundError as e:
                print(f"  FEHLT tir -> {e}")
                continue
        elif key == "bgld":
            p = ws.WIDMUNG / "burgenland" / "WIDMUNGSFLAECHEN.zip"
        elif key == "stmk_flaewi":
            p = ws.WIDMUNG / "steiermark" / "Flaewi.shp.zip"
        elif key == "stmk_bauland":
            p = ws.WIDMUNG / "steiermark" / "Bauland.zip"
        elif key == "noe":
            p = ws.WIDMUNG / "niederoesterreich" / "RRU_WI_HUELLE.gpkg"
        elif key == "ooe":
            p = ws.WIDMUNG / "oberoesterreich" / "FLWI_WIDMUNGEN_F.zip"
        elif key == "sbg":
            p = ws.WIDMUNG / "salzburg" / "Flaechenwidmung_Shapefile.zip"
        elif key == "vbg":
            p = ws.WIDMUNG / "vorarlberg" / "fwp_flaeche.gpkg"
        elif key == "wien":
            p = ws.WIDMUNG / "wien" / "genflwidmung_wien.geojson"
        else:
            continue
        print(f"  {'OK ' if p.exists() else 'FEHLT'} {key:15s} -> {p}")
except Exception as e:
    print(f"  IMPORT/CHECK FEHLER: {e!r}")

print()
print("=" * 70)
print("3) Repo-weite Suche nach alten Verzeichnis-/Dateinamen")
print("   (ohne .git/, docs/, scratchpad)")
print("=" * 70)

old_patterns = [
    "admin_boundaries",
    "adressregister",
    "new_widmungs_data",
    "flächenwidmungen",
    "naturschutzgebiete",
    "nö_zonierung",
    "data/luca_zonen",
    "data/DGM_R25.tif",
    "data/AUT_power-density",
    "data/austria-260330",
    "data/zonierung_noe.json",
    "data/WK_Eignungszonen.zip",
    "data/RED_III",
]

# git ls-files to respect .gitignore-like scoping but we also want untracked
# non-ignored files; use plain find, excluding .git, docs, scratchpad, and data/ itself
# (data/ contents are gitignored raw data, not code).
exclude_dirs = {".git", "docs", "scratchpad"}

def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(root)
        parts = set(rel.parts)
        if parts & exclude_dirs:
            continue
        # skip binary-ish / huge data dirs by extension heuristics not needed;
        # data/ itself is gitignored and mostly absent except README.md, fine to scan too.
        yield p

# Scope: git-tracked files (this excludes the gitignored data/ tree except
# data/README.md, which IS tracked) plus data/README.md explicitly in case
# it's untracked in this worktree. This avoids scanning multi-GB raw data.
tracked = subprocess.run(
    ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True
).stdout.splitlines()
candidate_files = []
for rel in tracked:
    relp = Path(rel)
    if set(relp.parts) & exclude_dirs:
        continue
    candidate_files.append(ROOT / rel)
# make sure data/README.md is included even if untracked for some reason
readme = ROOT / "data" / "README.md"
if readme.exists() and readme not in candidate_files:
    candidate_files.append(readme)

hits = []
for pat in old_patterns:
    proc = subprocess.run(
        ["grep", "-ln", "--binary-files=without-match", "-F", pat, *[str(f) for f in candidate_files]],
        capture_output=True, text=True,
    )
    matched_files = [l for l in proc.stdout.splitlines() if l.strip()]
    for f in matched_files:
        proc2 = subprocess.run(["grep", "-n", "-F", pat, f], capture_output=True, text=True)
        for l in proc2.stdout.splitlines():
            hits.append((pat, f"{f}:{l}"))

if not hits:
    print("  Keine Treffer - sauber.")
else:
    for pat, l in hits:
        print(f"  [{pat}] {l}")

print()
print("Fertig.")
