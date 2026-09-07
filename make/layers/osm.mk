# Paket W2.3 (docs/rewrite/PLAN.md §7) - OSM-Restlayer + Infrastruktur-/
# Flughafenmasken. Siehe README.md in diesem Verzeichnis für die Konvention
# und pipeline/layers/osm.py für die Logik.

.PHONY: layer-osm
layer-osm:
	uv run python -m pipeline.layers.osm
