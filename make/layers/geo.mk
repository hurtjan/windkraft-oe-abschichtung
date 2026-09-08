# Paket W2.4 - siehe make/layers/README.md für die Konvention und
# pipeline/layers/geo.py für den Modul-Docstring (Umfang, Ein-/Ausgaben,
# Fingerabdruck-Konvention).
#
# Schreibt NICHT nach output/abschichtung_widmung_v2/distance_layers/
# (historisch das geteilte, read-only-symlinkte Checkpoint-Verzeichnis, seit
# W6.1 nicht mehr im Repo) - Ziel ist pipeline.contract.DERIVED_LAYERS
# (derived/layers/), privat in diesem Worktree.
# --source-dir (Default: output/abschichtung_widmung_v2/distance_layers) war
# seit W5.P1 nur noch der RÜCKFALL für die 8 externen Quell-Checkpoints aus
# W2.1/W2.3 - primär liest pipeline.layers.geo dieselben acht Namen zuerst
# aus derived/layers/ (siehe pipeline/layers/geo.py:_source_layer_path()).
# Seit W6.1 ist dieser Rückfall entfernt (das Verzeichnis existiert nicht
# mehr): fehlt der Checkpoint unter derived/layers/, bricht der Aufruf jetzt
# sofort ab, statt zurückzufallen.
#
# W5.P1 (docs/rewrite/PLAN.md §13.6, "Die letzte output/-Abhängigkeit"):
# build_hig_family_sources() braucht 5 der 8 Checkpoints aus layer-hig,
# build_v2_buffers() 3 weitere aus layer-hig (nonresidential_hulls_source)
# bzw. layer-osm (cableway_buildings_source, general_buildings_source) -
# macht 6 von hig, 2 von osm, zusammen alle 8 required in
# pipeline/layers/geo.py:_check_required_sources(). Ohne diese
# Reihenfolge liest geo entweder aus einem leeren derived/layers/ (bricht ab)
# oder fällt still auf die run1-Vergleichsbasis zurück - beides der
# Befund, den dieses Paket behebt.
.PHONY: layer-geo
layer-geo: layer-hig layer-osm
	uv run python -m pipeline.layers.geo
