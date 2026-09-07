#!/usr/bin/env python3
"""Merge six graph fragments into one canonical dataflow graph.

Reads frag_A..frag_F JSON files from docs/dataflow/src/fragments/,
normalizes node ids, deduplicates nodes and edges, computes derived fields
(in/out-degree, stage, orphan/dead-end flags), and writes
docs/dataflow/{flow_graph.json,nodes.tsv,edges.tsv,README.md}.

Step 1 of 3 in the dataflow-graph generation chain:
    python3 docs/dataflow/src/1_merge.py
    python3 docs/dataflow/src/2_normalize.py
    python3 docs/dataflow/src/3_inject.py

Run from anywhere; all paths are resolved relative to the repo root (found
via this file's location), unless the DATAFLOW_ROOT environment variable
is set, in which case it is used as the repo root instead (used for
verification runs against a throwaway copy of docs/dataflow/).

README.md under docs/dataflow/ is hand-maintained; this script only ever
generates the generic version once, on first run. If the file already
exists, it is left alone -- pass --write-readme to overwrite it with the
generic version anyway (this discards any hand edits).
"""
import json
import re
import os
import sys
import datetime
import collections
from pathlib import Path

# docs/dataflow/src/1_merge.py -> parents[0]=src, [1]=dataflow, [2]=docs, [3]=repo root
ROOT = Path(os.environ.get("DATAFLOW_ROOT", Path(__file__).resolve().parents[3]))
OUTDIR = ROOT / "docs" / "dataflow"
FRAGDIR = OUTDIR / "src" / "fragments"

FRAGMENTS = [
    ("frag_A", "frag_A_widmung.json"),
    ("frag_B", "frag_B_preprocessing.json"),
    ("frag_C", "frag_C_data.json"),
    ("frag_D", "frag_D_package.json"),
    ("frag_E", "frag_E_output.json"),
    ("frag_F", "frag_F_control.json"),
]

# ---------------------------------------------------------------------------
# 1. Load fragments
# ---------------------------------------------------------------------------
frag_data = {}
for tag, fname in FRAGMENTS:
    with open(FRAGDIR / fname, encoding="utf-8") as f:
        frag_data[tag] = json.load(f)

# ---------------------------------------------------------------------------
# 2. Node-id normalization
# ---------------------------------------------------------------------------
DISTANCE_LAYER_RE = re.compile(r"^.*/distance_layers/([^/]+)\.tif$")
GLOB_RE = re.compile(r"\{[^}]*\}")

KNOWN_SHORT_CFG_KEYS = {
    "data_dir", "vgd", "osm_dir", "wind_pd_150", "wind_pd_100", "dgm",
    "nsg_zip", "nsg_gpkg", "nsg_layers", "powerlines_gpkg", "output_dir",
}


def strip_dotslash(p):
    if p.startswith("./"):
        p = p[2:]
    return p


# Explicit variant aliases: parametrized ids (CLI-arg placeholders like
# "<zoning_dir>/x.gpkg") that denote the SAME concrete artifact as a node
# already discovered (with a literal path) by another fragment. Verified by
# cross-checking fixed filenames / notes against frag_C/frag_E's concrete
# nodes. Generic per-class templates that do NOT denote one specific file
# (e.g. "<layer_dir>/<name>.tif" - the generic checkpoint-raster I/O helper,
# or "<raster>.bands.json" - the generic per-raster manifest pattern, or
# "<osm_pbf_cache_dir>/*.osm.pbf|*.geojsonseq" - a bbox/layer-keyed cache of
# many different files) are deliberately NOT aliased here - merging them into
# one concrete instance would misrepresent a many-to-one mechanism as one file.
ALIAS_DIR_TEMPLATE = {
    "<zoning_dir>/": "output/abschichtung_widmung_v2/zoning_vectors/",
    "<noe_dir>/": "output/noe/",
}
ALIAS_EXACT = {
    "<noe_dir>/pdf_hig_source_*.geojson(+_wgs84)": "output/noe/pdf_hig_source_*.geojson",
    "<cache_dir>/adressen_31287.parquet": "data/adressregister/adressen_31287.parquet",
    "<cache_dir>/bev_gebaeude_31287.parquet": "data/adressregister/bev_gebaeude_31287.parquet",
    "<cache_dir>/flawi_ktn_gpkg.gpkg": "output/abschichtung_widmung_v2/zoning_vectors/_cache/flawi_ktn_gpkg.gpkg",
    # explicitly flagged "vermutlich" (presumed, unverified) by frag_D itself;
    # merged because it names an exact candidate path and matches a node
    # frag_A/frag_B/frag_E already discovered independently - kept `uncertain`.
    "<dkm_parquet>": "output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet",
}
ALIAS_UNCERTAIN = {"<dkm_parquet>"}


def apply_alias(raw_id):
    if raw_id in ALIAS_EXACT:
        return ALIAS_EXACT[raw_id]
    for prefix, repl in ALIAS_DIR_TEMPLATE.items():
        if raw_id.startswith(prefix):
            return repl + raw_id[len(prefix):]
    return None


def normalize_id(node):
    """Return the canonical node id for a single fragment's node object."""
    raw_id = node["id"]
    kind = node.get("kind")
    path = node.get("path") or ""

    aliased = apply_alias(raw_id)
    if aliased is not None:
        return aliased

    # (a) Checkpoint layer: anything writing to .../distance_layers/<name>.tif
    m = DISTANCE_LAYER_RE.match(path)
    if m:
        return f"layer:{m.group(1)}"
    if raw_id.startswith("layer:"):
        return raw_id

    # (b) Config keys -> cfg:<key> (canonical key form is "paths.<name>" for
    # the 11 keys resolved by windkraft/config.py; short forms like "cfg:vgd"
    # get the "paths." prefix restored).
    if kind == "config_key" or raw_id.startswith(("cfg:", "config:", "config_key:")):
        key = raw_id.split(":", 1)[1] if ":" in raw_id else raw_id
        if "." not in key and key in KNOWN_SHORT_CFG_KEYS:
            key = f"paths.{key}"
        return f"cfg:{key}"

    # (c) Make targets -> make:<target>
    if kind == "make_target" or raw_id.startswith("make:"):
        return raw_id if raw_id.startswith("make:") else f"make:{raw_id}"

    # (d) External binaries -> bin:<name> (only real external-tool nodes,
    # identified by having no path / empty path, as opposed to kind=="external"
    # used elsewhere in frag_A for out-of-repo-scope *scripts* which do have paths)
    if raw_id.startswith("bin:"):
        return raw_id

    # (e) Glob/group nodes: keep the cleaner "group:" wildcard form as a
    # repo-relative path with "*" wildcard instead of the "{a,b,c}" brace form.
    if raw_id.startswith("group:"):
        return strip_dotslash(raw_id.split(":", 1)[1])
    if GLOB_RE.search(path):
        return strip_dotslash(path)

    # (f) Files / scripts / modules / dirs with a genuine single repo path
    if path and not path.startswith("vermutlich") and "<" not in path:
        p = strip_dotslash(path)
        if kind == "dir":
            p = p.rstrip("/")
        return p

    # (g) Fallback: templated/placeholder ids (e.g. "<dkm_parquet>",
    # "<raster>.bands.json") - keep verbatim, they don't denote one concrete path.
    return raw_id


# id_map[tag][original_id] = normalized_id
id_map = collections.defaultdict(dict)
for tag, _ in FRAGMENTS:
    for n in frag_data[tag]["nodes"]:
        id_map[tag][n["id"]] = normalize_id(n)

# Reverse global index: original_id (any fragment) -> set of normalized ids
# seen for that exact string, used to resolve cross-fragment edge endpoints
# that reference another fragment's node by its *own* original id spelling.
global_original_to_norm = {}
for tag, _ in FRAGMENTS:
    for orig, norm in id_map[tag].items():
        global_original_to_norm.setdefault(orig, set()).add(norm)

# ---------------------------------------------------------------------------
# 3. Canonical `kind` derivation (fragments disagree, e.g. script vs module vs
# external for the same windkraft/ file) - derive deterministically from the
# normalized id / path instead of trusting any single fragment's `kind`.
# ---------------------------------------------------------------------------
def canonical_kind(norm_id, path_hint):
    if norm_id.startswith("layer:"):
        return "layer"
    if norm_id.startswith("cfg:"):
        return "config_key"
    if norm_id.startswith("make:"):
        return "make_target"
    if norm_id.startswith("bin:"):
        return "external"
    p = path_hint or norm_id
    if p.endswith("/") or (p and "." not in os.path.basename(p) and p in KNOWN_DIRS):
        return "dir"
    if p.startswith("windkraft/") and p.endswith(".py"):
        return "module"
    if p.endswith(".py"):
        return "script"
    return "file"


KNOWN_DIRS = set()
for tag, _ in FRAGMENTS:
    for n in frag_data[tag]["nodes"]:
        if n.get("kind") == "dir":
            p = strip_dotslash((n.get("path") or "").rstrip("/"))
            KNOWN_DIRS.add(p)

# ---------------------------------------------------------------------------
# 4. Node merge
# ---------------------------------------------------------------------------
RAW_CLASS_RANK = {  # higher = more specific/wins a silent tie
    "code": 5,
    "manual": 4,
    "derived_elsewhere": 3,
    "derived_in_repo": 2,
    "raw": 1,
    "unknown": 0,
}

nodes = {}  # norm_id -> merged node dict
node_contrib = collections.defaultdict(list)  # norm_id -> [(tag, orig_node), ...]

for tag, _ in FRAGMENTS:
    for n in frag_data[tag]["nodes"]:
        norm = id_map[tag][n["id"]]
        node_contrib[norm].append((tag, n))

conflicts = []

for norm_id, contribs in node_contrib.items():
    sources = sorted({tag for tag, _ in contribs})
    raw_classes = [n.get("raw_class") for _, n in contribs]
    layers = [n.get("layer") for _, n in contribs]

    distinct_raw = sorted(set(raw_classes))
    distinct_layer = sorted(set(x for x in layers if x is not None))

    conflict_entry = {}
    if len(distinct_raw) > 1:
        conflict_entry["raw_class"] = distinct_raw
    if len(distinct_layer) > 1:
        conflict_entry["layer"] = distinct_layer

    if conflict_entry:
        conflict_entry["sources"] = sources
        conflict_entry["node"] = norm_id
        conflicts.append(conflict_entry)

    # winner raw_class = most specific by rank
    best_raw = max(raw_classes, key=lambda rc: RAW_CLASS_RANK.get(rc, -1))
    # winner layer = majority vote, tie-break by fragment order (A..F)
    if distinct_layer:
        counts = collections.Counter(x for x in layers if x is not None)
        maxcount = max(counts.values())
        candidates = [l for l, c in counts.items() if c == maxcount]
        if len(candidates) == 1:
            best_layer = candidates[0]
        else:
            # tie: first candidate in original fragment order
            best_layer = next(l for _, n in contribs if (l := n.get("layer")) in candidates)
    else:
        best_layer = None

    # path: prefer the longest non-"vermutlich"/non-glob concrete path
    paths = [n.get("path") for _, n in contribs if n.get("path")]
    concrete_paths = [p for p in paths if p and not p.startswith("vermutlich") and "<" not in p]
    path_val = None
    if concrete_paths:
        path_val = max(concrete_paths, key=len)
    elif paths:
        path_val = paths[0]

    kind_val = canonical_kind(norm_id, path_val)

    # label: prefer longest
    labels = [n.get("label") for _, n in contribs if n.get("label")]
    label_val = max(labels, key=len) if labels else norm_id

    # notes: union of distinct notes, tagged by source
    notes_parts = []
    seen_notes = set()
    for t, n in contribs:
        note = (n.get("notes") or "").strip()
        if note and note not in seen_notes:
            seen_notes.add(note)
            notes_parts.append(f"[{t}] {note}")
    notes_val = " | ".join(notes_parts)

    # size / mtime / uncertain: carry through if present (first non-null)
    size_val = next((n.get("size") for _, n in contribs if n.get("size")), None)
    mtime_val = next((n.get("mtime") for _, n in contribs if n.get("mtime")), None)
    uncertain_val = any(n.get("uncertain") for _, n in contribs) or \
        any(n["id"] in ALIAS_UNCERTAIN for _, n in contribs)

    merged = {
        "id": norm_id,
        "kind": kind_val,
        "layer": best_layer,
        "path": path_val,
        "label": label_val,
        "raw_class": best_raw,
        "notes": notes_val,
        "sources": sources,
    }
    if size_val:
        merged["size"] = size_val
    if mtime_val:
        merged["mtime"] = mtime_val
    if uncertain_val:
        merged["uncertain"] = True
    if conflict_entry:
        merged["conflict"] = {k: v for k, v in conflict_entry.items() if k in ("raw_class", "layer", "sources")}

    nodes[norm_id] = merged

dup_merges = sum(1 for c in node_contrib.values() if len(c) > 1)

# ---------------------------------------------------------------------------
# 5. Edge endpoint resolution + edge dedup
# ---------------------------------------------------------------------------
stubs = {}


def resolve_endpoint(tag, endpoint):
    """Resolve an edge endpoint string (as written in fragment `tag`) to a
    canonical node id, creating a stub node if nothing matches."""
    aliased = apply_alias(endpoint)
    if aliased is not None:
        return aliased
    # 1) exact match against this fragment's own id map
    if endpoint in id_map[tag]:
        return id_map[tag][endpoint]
    # 2) exact string match against any other fragment's original ids
    if endpoint in global_original_to_norm:
        candidates = global_original_to_norm[endpoint]
        if len(candidates) == 1:
            return next(iter(candidates))
        # multiple different normalizations for same literal string (rare) -
        # prefer one that is already a known node
        for c in candidates:
            if c in nodes:
                return c
        return next(iter(candidates))
    # 3) already-canonical forms used directly in edges (cfg:/make:/bin:/layer:)
    if endpoint.startswith(("cfg:", "make:", "bin:", "layer:")):
        if endpoint.startswith("cfg:"):
            key = endpoint.split(":", 1)[1]
            if "." not in key and key in KNOWN_SHORT_CFG_KEYS:
                key = f"paths.{key}"
            return f"cfg:{key}"
        return endpoint
    # 4) treat as a plain repo-relative path
    p = strip_dotslash(endpoint)
    if p in nodes:
        return p
    m = DISTANCE_LAYER_RE.match(p)
    if m:
        return f"layer:{m.group(1)}"
    # 5) genuine gap -> stub node
    if p not in nodes and p not in stubs:
        stubs[p] = {
            "id": p,
            "kind": "unknown",
            "layer": None,
            "path": p if "/" in p else None,
            "label": p,
            "raw_class": "unknown",
            "notes": f"Stub: referenziert von Kante in {tag}, keine Node-Definition in keinem Fragment gefunden.",
            "sources": [tag],
            "stub": True,
        }
    return p


edge_groups = collections.defaultdict(lambda: {"evidence": [], "notes": [], "optional_votes": [], "sources": set()})

for tag, _ in FRAGMENTS:
    for e in frag_data[tag]["edges"]:
        frm = resolve_endpoint(tag, e["from"])
        to = resolve_endpoint(tag, e["to"])
        kind = e.get("kind")
        key = (frm, to, kind)
        g = edge_groups[key]
        ev = e.get("evidence")
        if ev:
            tagged = f"[{tag}] {ev}"
            if tagged not in g["evidence"]:
                g["evidence"].append(tagged)
        note = (e.get("note") or "").strip()
        if note and note not in g["notes"]:
            g["notes"].append(note)
        g["optional_votes"].append(bool(e.get("optional")))
        g["sources"].add(tag)

edges = []
for (frm, to, kind), g in edge_groups.items():
    optional = all(g["optional_votes"])  # required if ANY source marks it required
    edges.append({
        "from": frm,
        "to": to,
        "kind": kind,
        "optional": optional,
        "evidence": g["evidence"],
        "note": " | ".join(g["notes"]),
        "sources": sorted(g["sources"]),
    })

edge_dup_merges = sum(1 for g in edge_groups.values() if len(g["sources"]) > 1)

# merge stubs into nodes
for sid, snode in stubs.items():
    nodes[sid] = snode

# ---------------------------------------------------------------------------
# 6. in_degree / out_degree
# ---------------------------------------------------------------------------
for n in nodes.values():
    n["in_degree"] = 0
    n["out_degree"] = 0
for e in edges:
    if e["from"] in nodes:
        nodes[e["from"]]["out_degree"] += 1
    if e["to"] in nodes:
        nodes[e["to"]]["in_degree"] += 1

# ---------------------------------------------------------------------------
# 7. stage assignment
# ---------------------------------------------------------------------------
STAGE_ORDER = ["stage0", "stage1", "stage2", "stage3", "stage4", "stage5",
               "downstream", "control", "library", "input"]
STAGE_RANK = {s: i for i, s in enumerate(STAGE_ORDER)}

WIDMUNG_STAGE_RE = re.compile(r"^scripts/widmung_v2/0([1-5])_")


def static_stage(node_id, path):
    p = path or node_id
    if node_id.startswith(("cfg:", "make:", "bin:")):
        return "control"
    if p.startswith("data/"):
        return "input"
    if p.startswith("windkraft/"):
        return "library"
    if p.startswith("scripts/noe/") or p.startswith("scripts/preprocessing/"):
        return "stage0"
    m = WIDMUNG_STAGE_RE.match(p)
    if m:
        return f"stage{m.group(1)}"
    if p.startswith("scripts/webmap/") or p.startswith("scripts/analysis/"):
        return "downstream"
    if p.startswith("docs/"):
        return "downstream"
    if p in ("Makefile", "pyproject.toml", ".gitignore", "config.json") or \
       p.startswith("tests/") or p.startswith("tools/"):
        return "control"
    return None


# checkpoint layers: derive stage from the *set* of writer scripts of that
# layer (edges kind == "writes"/"creates"), taking the earliest stage.
writers = collections.defaultdict(list)  # target_id -> [writer_id, ...]
for e in edges:
    if e["kind"] in ("writes", "creates"):
        writers[e["to"]].append(e["from"])

resolved_stage = {}
for nid, n in nodes.items():
    s = static_stage(nid, n.get("path"))
    if s:
        resolved_stage[nid] = s

unresolved = [nid for nid in nodes if nid not in resolved_stage]

changed = True
while changed:
    changed = False
    for nid in unresolved:
        if nid in resolved_stage:
            continue
        cand_stages = []
        for w in writers.get(nid, []):
            if w in resolved_stage:
                cand_stages.append(resolved_stage[w])
        if cand_stages:
            best = min(cand_stages, key=lambda s: STAGE_RANK.get(s, 999))
            resolved_stage[nid] = best
            changed = True

# path-substring fallback for remaining (orphan outputs w/o writer edge)
FALLBACK_RULES = [
    ("zoning_vectors", "stage1"),
    ("osm_pbf_layers", "stage3"),
    ("distance_layers", "stage2"),
    ("output/noe/", "stage0"),
    ("output/kataster", "stage0"),
    ("output/abschichtung_widmung_v2/osm_wka_distance_zones", "stage4"),
]
for nid, n in nodes.items():
    if nid in resolved_stage:
        continue
    p = n.get("path") or nid
    for substr, stage in FALLBACK_RULES:
        if substr in p:
            resolved_stage[nid] = stage
            break

for nid, n in nodes.items():
    n["stage"] = resolved_stage.get(nid)

still_unresolved = [nid for nid, n in nodes.items() if n["stage"] is None]

# ---------------------------------------------------------------------------
# 8. Endprodukte + flags
# ---------------------------------------------------------------------------
FINAL_PRODUCTS = {
    "output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif",
    "output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.bands.json",
}


def is_final_product(nid, path):
    if nid in FINAL_PRODUCTS:
        return True
    p = path or nid
    if p.startswith("docs/") and p.endswith(".md"):
        return True
    return False


for nid, n in nodes.items():
    flags = {}
    if n.get("stub"):
        flags["stub"] = True
    if n["in_degree"] == 0 and n["raw_class"] not in ("raw", "manual", "code"):
        flags["orphan_source"] = True
    if n["out_degree"] == 0 and n["kind"] != "make_target" and not is_final_product(nid, n.get("path")):
        flags["dead_end"] = True
    n["flags"] = flags

# ---------------------------------------------------------------------------
# 9. Write outputs
# ---------------------------------------------------------------------------
os.makedirs(OUTDIR, exist_ok=True)

meta = {
    "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "fragments": [fname for _, fname in FRAGMENTS],
    "fragment_node_counts": {tag: len(frag_data[tag]["nodes"]) for tag, _ in FRAGMENTS},
    "fragment_edge_counts": {tag: len(frag_data[tag]["edges"]) for tag, _ in FRAGMENTS},
    "node_count": len(nodes),
    "edge_count": len(edges),
    "node_duplicate_merges": dup_merges,
    "edge_duplicate_merges": edge_dup_merges,
    "conflict_count": len(conflicts),
    "stub_count": len(stubs),
}

flow_graph = {
    "meta": meta,
    "nodes": [nodes[k] for k in sorted(nodes)],
    "edges": sorted(edges, key=lambda e: (e["from"], e["to"], e["kind"])),
    "conflicts": conflicts,
    "stubs": sorted(stubs.keys()),
}

with open(os.path.join(OUTDIR, "flow_graph.json"), "w", encoding="utf-8") as f:
    json.dump(flow_graph, f, ensure_ascii=False, indent=2)


def tsv_escape(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return s


def truncate(s, n=200):
    s = tsv_escape(s)
    return s if len(s) <= n else s[: n - 1] + "…"


with open(os.path.join(OUTDIR, "nodes.tsv"), "w", encoding="utf-8") as f:
    f.write("\t".join(["id", "kind", "layer", "stage", "raw_class", "in_degree",
                        "out_degree", "flags", "path", "label", "notes"]) + "\n")
    for nid in sorted(nodes):
        n = nodes[nid]
        flag_str = ",".join(sorted(k for k, v in n["flags"].items() if v))
        row = [
            n["id"], n["kind"], n.get("layer") or "", n.get("stage") or "",
            n["raw_class"], n["in_degree"], n["out_degree"], flag_str,
            n.get("path") or "", n.get("label") or "", truncate(n.get("notes")),
        ]
        f.write("\t".join(tsv_escape(x) for x in row) + "\n")

with open(os.path.join(OUTDIR, "edges.tsv"), "w", encoding="utf-8") as f:
    f.write("\t".join(["from", "to", "kind", "optional", "evidence", "note"]) + "\n")
    for e in sorted(edges, key=lambda e: (e["from"], e["to"], e["kind"])):
        row = [
            e["from"], e["to"], e["kind"], str(e["optional"]).lower(),
            tsv_escape(";".join(e["evidence"])), tsv_escape(e["note"]),
        ]
        f.write("\t".join(tsv_escape(x) for x in row) + "\n")

README = """# docs/dataflow — kanonischer Datenfluss-Graph

Dieser Graph fasst sechs unabhängig erstellte Graph-Fragmente
(`frag_A_widmung` .. `frag_F_control`, siehe `flow_graph.json` -> `meta.fragments`)
zu einem einzigen, dedupliziertem Datenfluss-Graphen der Windkraft-Pipeline
zusammen. Erzeugt von `docs/dataflow/src/1_merge.py` (siehe `README.md`
Abschnitt "Neu erzeugen").

## Was ist ein Node?

Ein Node ist eine Datei, ein Skript/Modul, ein Checkpoint-Layer (Zwischen-
Raster unter `output/.../distance_layers/*.tif`, id-Form `layer:<name>`),
ein Config-Key aus `config.json` (id-Form `cfg:paths.<key>`), ein
Make-Target (`make:<target>`) oder ein externes Kommandozeilen-Tool
(`bin:<name>`). Node-ids sind, wo sinnvoll, repo-relative Pfade ohne
führendes `./`.

Felder je Node (siehe `nodes.tsv` / `flow_graph.json`):

- `kind` — file | script | module | dir | layer | config_key | make_target | external | unknown
- `layer` — grobe Herkunftsklasse aus den Fragmenten: code | raw | intermediate | output | config
- `stage` — Pipelinestufe: `stage0` (scripts/noe, scripts/preprocessing + deren
  Outputs), `stage1`..`stage5` (scripts/widmung_v2/01..05 + deren Outputs),
  `downstream` (webmap/analysis/docs), `control` (Makefile/config/pyproject/
  tools/tests), `input` (data/*), `library` (windkraft/*)
- `raw_class` — manual | derived_elsewhere | derived_in_repo | raw | unknown | code
  (bei widersprüchlichen Angaben zwischen Fragmenten: spezifischster Wert nach
  Rangfolge `code > manual > derived_elsewhere > derived_in_repo > raw > unknown`;
  der volle Widerspruch steht in `conflicts` in `flow_graph.json`)
- `in_degree` / `out_degree` — Anzahl eingehender/ausgehender Kanten nach Dedup
- `flags` — kommagetrennt: `stub` (Kante zeigte auf keinen bekannten Node -> Lücke
  der Inventur), `orphan_source` (in_degree==0 und raw_class nicht raw/manual/code
  -> vermutlich unvollständig erfasste Herkunft), `dead_end` (out_degree==0, kein
  Make-Target, kein deklariertes Endprodukt -> vermutlich totes Artefakt oder
  Lücke in der Kantenerfassung)

Endprodukte (nie als `dead_end` markiert): das finale GeoTIFF
`output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif`,
dessen `.bands.json`, sowie alle Berichte unter `docs/*.md`.

## Kanten

Eine Zeile in `edges.tsv` je (from, to, kind) nach Dedup. `evidence` bündelt
alle Belegstellen aus allen Quellfragmenten (`;`-getrennt, `[frag_X] ...`
präfixiert). `optional=true` nur wenn *alle* beitragenden Fragmente die Kante
als optional einstuften; widerspricht auch nur ein Fragment, gilt die Kante
als erforderlich.

## Beispiel-Greps

Alle Sackgassen (dead ends):

    awk -F'\\t' 'NR>1 && $8 ~ /dead_end/' docs/dataflow/nodes.tsv

Alle Inputs, die NICHT roh sind (also abgeleitet/unklar, obwohl unter data/):

    awk -F'\\t' 'NR>1 && $4=="input" && $5!="raw"' docs/dataflow/nodes.tsv

Alle Leser einer bestimmten Datei (z.B. windkraft/config.py):

    awk -F'\\t' 'NR>1 && $2=="windkraft/config.py"' docs/dataflow/edges.tsv

Alle Stub-Nodes (Lücken der Inventur):

    awk -F'\\t' 'NR>1 && $8 ~ /stub/' docs/dataflow/nodes.tsv

Alle Nodes mit widersprüchlichen raw_class/layer-Angaben zwischen Fragmenten:

    python3 -c "import json; d=json.load(open('docs/dataflow/flow_graph.json')); [print(c) for c in d['conflicts']]"

Alle Kanten aus einem bestimmten Make-Target (z.B. make:widmung-v2):

    awk -F'\\t' 'NR>1 && $1=="make:widmung-v2"' docs/dataflow/edges.tsv
"""

README_PATH = os.path.join(OUTDIR, "README.md")
WRITE_README = "--write-readme" in sys.argv
if WRITE_README or not os.path.exists(README_PATH):
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(README)
else:
    print(
        f"README.md exists at {README_PATH}; not overwriting "
        "(it is hand-maintained -- pass --write-readme to force)."
    )

# ---------------------------------------------------------------------------
# 10. Report to stdout (for the calling agent, not part of the repo output)
# ---------------------------------------------------------------------------
print("=== MERGE REPORT ===")
print(f"final nodes: {len(nodes)}  (dupe merges: {dup_merges})")
print(f"final edges: {len(edges)}  (dupe merges: {edge_dup_merges})")
print(f"conflicts: {len(conflicts)}")
for c in conflicts:
    print("  ", c)
print(f"stubs: {len(stubs)}")
for s in sorted(stubs):
    print("  ", s)
print("stage counts:")
stage_counts = collections.Counter(n.get("stage") for n in nodes.values())
for s in STAGE_ORDER + [None]:
    if stage_counts.get(s):
        print(f"  {s}: {stage_counts[s]}")
print(f"still unresolved stage: {len(still_unresolved)}")
for nid in still_unresolved:
    print("   unresolved:", nid, nodes[nid].get("path"))
dead_ends = [nid for nid, n in nodes.items() if n["flags"].get("dead_end")]
orphans = [nid for nid, n in nodes.items() if n["flags"].get("orphan_source")]
print(f"dead_end count: {len(dead_ends)}")
print(f"orphan_source count: {len(orphans)}")
