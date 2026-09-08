# Prep: Gelände und Wind (docs/rewrite/PLAN.md §7 W1.P6, Auflösung in §13.5).
# Konvention siehe make/prep/README.md, Vorlage make/prep/_beispiel.mk.txt.
#
# Keine Umformung, nur Gitterprüfung: pipeline/prep/terrain.py liest die
# beiden Rohraster aus contract.RAW["gelaende"], schreibt einen
# menschenlesbaren Prüfbericht und den gemeinsamen Fingerabdruck nach
# contract.PREP["gelaende"] (derived/prep/gelaende/) - kein neues TIF.

.PHONY: prep-gelaende
prep-gelaende:
	uv run python -m pipeline.prep.terrain
