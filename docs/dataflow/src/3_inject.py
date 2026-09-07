#!/usr/bin/env python3
"""Reduce docs/dataflow/flow_graph.json to a compact object, inject it into
the docs/dataflow/src/template.html page in place of the __GRAPH_JSON__
placeholder, and wrap the result in the standalone-HTML skeleton
(<!doctype>/<head>/<body>) to produce docs/dataflow/flow_diagram.html.

Step 3 of 3 in the dataflow-graph generation chain (see docs/dataflow/
README.md, Abschnitt "Neu erzeugen"). Run from anywhere; paths resolve
relative to the repo root found via this file's location, unless
DATAFLOW_ROOT is set (used for verification runs against a throwaway copy
of docs/dataflow/).
"""
import json
import os
from pathlib import Path

# docs/dataflow/src/3_inject.py -> parents[0]=src, [1]=dataflow, [2]=docs, [3]=repo root
ROOT = Path(os.environ.get("DATAFLOW_ROOT", Path(__file__).resolve().parents[3]))
DF = ROOT / "docs" / "dataflow"

SRC_GRAPH = DF / "flow_graph.json"
SRC_TEMPLATE = DF / "src" / "template.html"
DST_HTML = DF / "flow_diagram.html"

FLAG_KEYS = (
    "unused",
    "external_input",
    "true_raw",
    "terminal_product",
    "unreachable",
    "verified_dead",
    "dead_end",
)

# Standalone-HTML skeleton wrapped around the template's <title>..</script>
# body. Taken verbatim from the existing docs/dataflow/flow_diagram.html so
# that re-running this chain reproduces byte-identical framing.
SKELETON_HEAD = (
    '<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    "<style>\n:root{color-scheme:light dark}\nbody{margin:0}\n"
    "img{max-width:100%}\n[hidden]{display:none!important}\n</style>\n"
)
SKELETON_MID = "</head>\n<body>\n\n\n"
SKELETON_TAIL = "\n</body>\n</html>\n"


def trunc(s, n):
    if s is None:
        return None
    return s if len(s) <= n else s[:n]


def build_meta(meta):
    out = {}
    ts_key = "generated" if "generated" in meta else None
    if ts_key is None:
        for k in meta:
            if "generat" in k or "timestamp" in k or k in ("fixed_at",):
                ts_key = k
                break
    if ts_key is None:
        for k in ("generated_at", "fixed_at"):
            if k in meta:
                ts_key = k
                break
    if ts_key is not None and meta.get(ts_key):
        out[ts_key] = meta[ts_key]
    if "schema_version" in meta and meta["schema_version"] is not None:
        out["schema_version"] = meta["schema_version"]
    return out


def build_node(n):
    out = {}
    for key in ("id", "kind", "layer", "stage", "raw_class", "path", "label"):
        v = n.get(key)
        if v not in (None, ""):
            out[key] = v
    if n.get("size") not in (None, ""):
        out["size"] = n["size"]
    notes = trunc(n.get("notes"), 320)
    if notes:
        out["notes"] = notes
    for key in ("producers", "consumers"):
        v = n.get(key)
        if v not in (None, ""):
            out[key] = v
    flags = n.get("flags") or {}
    for fk in FLAG_KEYS:
        if bool(flags.get(fk)):
            out[fk] = True
    return out


def build_edge(e):
    out = {}
    for key in ("from", "to", "kind"):
        v = e.get(key)
        if v not in (None, ""):
            out[key] = v
    if e.get("flow") is False:
        out["flow"] = False
    if e.get("reversed") is True:
        out["reversed"] = True
    if e.get("derived") is True:
        out["derived"] = True
    if e.get("optional") is True:
        out["optional"] = True
    ev = e.get("evidence")
    if ev:
        out["evidence"] = ev[:3]
    note = trunc(e.get("note"), 160)
    if note:
        out["note"] = note
    return out


def main():
    with open(SRC_GRAPH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    reduced = {
        "meta": build_meta(graph.get("meta", {})),
        "nodes": [build_node(n) for n in graph.get("nodes", [])],
        "edges": [build_edge(e) for e in graph.get("edges", [])],
    }

    payload = json.dumps(reduced, separators=(",", ":"), ensure_ascii=False)
    payload = payload.replace("</", "<\\/")

    with open(SRC_TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    count = template.count("__GRAPH_JSON__")
    if count != 1:
        raise SystemExit(f"expected exactly 1 occurrence of __GRAPH_JSON__, found {count}")

    injected = template.replace("__GRAPH_JSON__", payload, 1)

    # Wrap the injected template body in the standalone-HTML skeleton, in
    # the same spot the skeleton's <body> tag was previously inserted by
    # hand: right after the last </style> block that precedes <header>.
    header_idx = injected.index("<header")
    style_end = injected.rindex("</style>\n", 0, header_idx) + len("</style>\n")

    final_html = (
        SKELETON_HEAD
        + injected[:style_end]
        + SKELETON_MID
        + injected[header_idx:]
        + SKELETON_TAIL
    )

    with open(DST_HTML, "w", encoding="utf-8") as f:
        f.write(final_html)

    print("nodes:", len(reduced["nodes"]))
    print("edges:", len(reduced["edges"]))
    print("payload bytes:", len(payload.encode("utf-8")))
    print("final html bytes:", len(final_html.encode("utf-8")))
    print("meta:", reduced["meta"])


if __name__ == "__main__":
    main()
