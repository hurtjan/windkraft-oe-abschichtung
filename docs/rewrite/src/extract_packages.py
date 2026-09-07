#!/usr/bin/env python3
"""Extract the work-package matrix embedded as a JS array literal in
docs/rewrite/umsetzung.html and write it out as packages.tsv and
packages.json.

The source page is handwritten and self-contained: the package list that
drives the on-page wave grid and table lives inline as a JS array called
`P` inside the <script> block at the end of the file. This script parses
that block with a JS-object-literal-tolerant regex/state-machine approach
(the array is not strict JSON: unquoted keys, single/double-quoted strings)
and re-serializes it as:

  - docs/rewrite/packages.tsv  -- flat, grep/awk-friendly (no tabs/newlines
    inside fields; owned paths are ";"-joined within their field)
  - docs/rewrite/packages.json -- the same records as a JSON array of objects

Run: python3 docs/rewrite/src/extract_packages.py
Paths resolve relative to this file's location (docs/rewrite/src/..).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # docs/rewrite/src -> repo root
REWRITE = ROOT / "docs" / "rewrite"
SRC_HTML = REWRITE / "umsetzung.html"
DST_TSV = REWRITE / "packages.tsv"
DST_JSON = REWRITE / "packages.json"

FIELDS = ["id", "wave", "group", "title", "owns", "depends", "acceptance"]


def extract_p_array_src(html_text):
    """Return the raw JS source text of the `var P = [ ... ];` array."""
    m = re.search(r"var\s+P\s*=\s*\[", html_text)
    if not m:
        raise SystemExit("Could not find 'var P = [' in source HTML")
    start = m.end() - 1  # index of the opening '['
    depth = 0
    i = start
    in_str = None
    while i < len(html_text):
        c = html_text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "'\"":
            in_str = c
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return html_text[start:i + 1]
        i += 1
    raise SystemExit("Unbalanced brackets while scanning P array")


def strip_line_comments(src):
    """Strip '// ...' line comments that live outside of string literals."""
    out = []
    i, n = 0, len(src)
    in_str = None
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in "'\"":
            in_str = c
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            if j == -1:
                break
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def js_object_literal_to_json(src):
    """Convert a small, well-behaved JS object/array literal (unquoted keys,
    single-quoted strings, no functions) into valid JSON text."""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "'":
            # single-quoted JS string -> double-quoted JSON string
            j = i + 1
            buf = []
            while j < n and src[j] != "'":
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if src[j] == '"':
                    buf.append('\\"')
                    j += 1
                    continue
                buf.append(src[j])
                j += 1
            out.append('"' + "".join(buf) + '"')
            i = j + 1
            continue
        if c == '"':
            # already double-quoted JSON-ish string; copy through, honoring escapes
            j = i + 1
            buf = ['"']
            while j < n and src[j] != '"':
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                buf.append(src[j])
                j += 1
            buf.append('"')
            out.append("".join(buf))
            i = j + 1
            continue
        if c.isalpha() or c == "_":
            # bare identifier: object key -> quote it
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            out.append('"' + src[i:j] + '"')
            i = j
            continue
        out.append(c)
        i += 1
    text = "".join(out)
    # strip trailing commas before ] or }
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text


def load_p_records():
    html_text = SRC_HTML.read_text(encoding="utf-8")
    p_src = extract_p_array_src(html_text)
    p_src = strip_line_comments(p_src)
    json_text = js_object_literal_to_json(p_src)
    return json.loads(json_text)


def clean_field(s):
    """Make a value TSV-safe: strip embedded HTML entities/tags left over
    from display strings, collapse whitespace, drop tabs/newlines."""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("&amp;", "&")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("\t", " ")
    return s


def to_record(raw):
    owns = [clean_field(o) for o in raw.get("owns", [])]
    return {
        "id": clean_field(raw.get("id")),
        "wave": clean_field(raw.get("w")),
        "group": clean_field(raw.get("g")),
        "title": clean_field(raw.get("t")),
        "owns": ";".join(owns),
        "depends": clean_field(raw.get("dep")),
        "acceptance": clean_field(raw.get("acc")),
    }


def write_tsv(records, path):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(FIELDS) + "\n")
        for r in records:
            f.write("\t".join(r[k] for k in FIELDS) + "\n")


def write_json(records, path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    raw_records = load_p_records()
    records = [to_record(r) for r in raw_records]
    write_tsv(records, DST_TSV)
    write_json(records, DST_JSON)
    print(f"Wrote {len(records)} package records to {DST_TSV} and {DST_JSON}")


if __name__ == "__main__":
    main()
