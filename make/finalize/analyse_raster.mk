# Zweites Produkt: out/abschichtung_analyse.tif + .bands.json (nur Analyse,
# nicht Teil des Konsumentenvertrags). Laeuft nach `finalize`, weil es das
# Raster von out/abschichtung.tif uebernimmt. Skip-if-unchanged ueber
# pipeline/fingerprint.py; `--force` erzwingt einen Neulauf.
.PHONY: analyse-raster
analyse-raster:
	uv run python -m pipeline.analyse_raster
