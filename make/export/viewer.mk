# make/export/viewer.mk — Paket W6.7 (docs/rewrite/PLAN.md).
#
# Siehe make/export/README.md fuer die Konvention (export-<domaene>, eigene
# Datei je Export-Paket, gelesen per -include make/export/*.mk im
# Haupt-Makefile).
#
# pipeline/export/viewer.py baut den Leaflet/OSM-Kartenviewer unter
# out/dashboard/ (index.html, manifest.json, layers/*.png) aus
# out/abschichtung.tif + out/abschichtung.bands.json. Explizite
# Abhaengigkeit von export-dashboard: dashboard.py ist die Pruefstufe und
# schreibt report.json zuerst; beide Ziele schreiben in denselben Ordner,
# aber unterschiedliche Dateien (report.json vs. index.html/manifest.json/
# layers/) - kein Konflikt, aber eine bewusste Reihenfolge.

.PHONY: export-viewer
export-viewer: export-dashboard
	uv run python -m pipeline.export.viewer
