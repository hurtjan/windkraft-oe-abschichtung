# make/prep/noe_sekrop.mk — Paket W1.P9 (docs/rewrite/PLAN.md §7).
#
# Zweistufige Domäne (siehe pipeline/contract.py:PREP["noe_sekrop"] und
# make/prep/README.md): Stufe a (Alignment - Georeferenzierung der
# PDF-Kartenseite) liest nur die vier GPTS-Eckpunkte und die Seitenhöhe,
# Stufe b (Vektorisierung) liest das Alignment-Ergebnis von a und filtert
# die PDF-Vektorpfade nach Farbe. `prep-noe-sekrop` ruft beide in der
# richtigen Reihenfolge auf - b liest das Ergebnis von a, nie umgekehrt
# (PLAN.md §3: "Jede Stufe darf nur aus der vorigen lesen"). Anders als bei
# `kataster`/`osm` steckt die Reihenfolge hier in einem einzigen Modul
# (`pipeline/prep/noe_sekrop.py`, nicht `a_.../b_...`-Untermodule) - beide
# Stufen sind günstig genug, dass eine eigene Datei je Stufe nur zusätzliche
# Indirektion wäre; run() reicht das Alignment-Dict direkt von a an b durch.
#
# Zielname mit Bindestrich (`prep-noe-sekrop`), nicht mit Unterstrich wie
# der Vertragsschlüssel (`noe_sekrop`) - siehe Bericht zu W1.P9. Damit
# `make prep` diese Datei trotzdem automatisch findet (PREP_TARGETS im
# Haupt-Makefile leitet den Namen aus dem Dateinamen ab: `prep-noe_sekrop`,
# mit Unterstrich), ist `prep-noe_sekrop` unten ein reiner Alias.

.PHONY: prep-noe-sekrop prep-noe-sekrop-a prep-noe-sekrop-b prep-noe_sekrop

prep-noe-sekrop-a:
	uv run python -c "from pipeline.prep import noe_sekrop; noe_sekrop.run_align()"

prep-noe-sekrop-b:
	uv run python -c "from pipeline.prep import noe_sekrop; noe_sekrop.run_vectorize()"

prep-noe-sekrop:
	uv run python -m pipeline.prep.noe_sekrop

# Alias für die automatische Aggregation in `make prep` (siehe oben).
prep-noe_sekrop: prep-noe-sekrop
