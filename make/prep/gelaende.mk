# Prep: Gelände und Wind (docs/rewrite/PLAN.md §7 W1.P6, Auflösung in §13.5).
# Konvention siehe make/prep/README.md, Vorlage make/prep/_beispiel.mk.txt.
#
# pipeline/prep/terrain.py liest die beiden Rohraster aus
# contract.RAW["gelaende"] und schreibt dgm.tif und wind_pd_150.tif exakt auf
# das 25-m-Zielgitter nach derived/prep/gelaende/ (plus Bericht und
# Fingerabdruck). Layer und Finalize lesen nur noch diese beiden TIFs.

.PHONY: prep-gelaende
prep-gelaende:
	uv run python -m pipeline.prep.terrain
