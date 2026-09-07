# make/prep/kataster.mk — Paket W1.P2 (docs/rewrite/PLAN.md §7).
#
# Zweistufige Domäne (siehe pipeline/contract.py:PREP["kataster"] und
# make/prep/README.md): Stufe a (NÖ-DXF-Polygonisierung) ist die teuerste
# Stufe der ganzen Kette, Stufe b (SHP-Export der übrigen acht
# Bundesländer + Zusammenführung mit Stufe a) ist vergleichsweise billig.
# `prep-kataster` ruft beide in der richtigen Reihenfolge auf - b liest
# das Ergebnis von a, nie umgekehrt (docs/rewrite/PLAN.md §3: "Jede Stufe
# darf nur aus der vorigen lesen").

.PHONY: prep-kataster prep-kataster-a prep-kataster-b

prep-kataster-a:
	uv run python -m pipeline.prep.kataster.a_noe_polygonize

prep-kataster-b:
	uv run python -m pipeline.prep.kataster.b_export_parquet

prep-kataster: prep-kataster-a prep-kataster-b
