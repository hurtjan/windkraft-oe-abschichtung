# Paket W2.3 (docs/rewrite/PLAN.md §7) - OSM-Restlayer + Infrastruktur-/
# Flughafenmasken. Siehe README.md in diesem Verzeichnis für die Konvention
# und pipeline/layers/osm.py für die Logik.
#
# W5.P1 (docs/rewrite/PLAN.md §13.6): läuft nach layer-hig, nicht weil
# pipeline.layers.osm ohne dessen Ausgaben abbricht (--legacy-cover-dir
# fängt das schon ab, siehe pipeline/layers/osm.py:_cover_layer_path()),
# sondern damit dieser Rückfall in einer sauberen Kette gar nicht erst
# gebraucht wird - und pipeline.layers.geo (das layer-osm-Ausgaben
# unbedingt braucht) danach garantiert aus build/layers/ statt aus der
# geteilten run1-Vergleichsbasis liest.
.PHONY: layer-osm
layer-osm: layer-hig
	uv run python -m pipeline.layers.osm
