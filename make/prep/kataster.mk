# make/prep/kataster.mk — Paket W1.P2 (docs/rewrite/PLAN.md §7).
#
# Dreistufige Domäne: Stufe a (NÖ-DXF-Polygonisierung, Zwischenstand nach
# derived/work/kataster/) ist die teuerste Stufe der ganzen Kette, Stufe b
# (SHP-Export der übrigen acht Bundesländer + Zusammenführung mit Stufe a)
# schreibt das große Kataster-GeoParquet, Stufe c (Streusiedlungs-Kandidaten,
# pipeline/prep/kataster/c_streusiedlung.py) schneidet daraus das kleine
# Produkt streusiedlung_*.parquet, das die Layer-Stufe liest. c braucht die
# Prep-Produkte widmung, noe_sekrop, adressen und gelaende.
# Weitergabe ohne Rohdaten: fehlen die Rohdaten, die Produkte sind aber da,
# überspringt jede Stufe sich selbst (pipeline/prep/share.py).

.PHONY: prep-kataster prep-kataster-a prep-kataster-b prep-kataster-c

prep-kataster-a:
	uv run python -m pipeline.prep.kataster.a_noe_polygonize

prep-kataster-b:
	uv run python -m pipeline.prep.kataster.b_export_parquet

prep-kataster-c: prep-widmung prep-noe_sekrop prep-adressen prep-gelaende
	uv run python -m pipeline.prep.kataster.c_streusiedlung

prep-kataster: prep-kataster-a prep-kataster-b prep-kataster-c
