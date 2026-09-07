# Paket W2.4 - siehe make/layers/README.md für die Konvention und
# pipeline/layers/geo.py für den Modul-Docstring (Umfang, Ein-/Ausgaben,
# Fingerabdruck-Konvention).
#
# Schreibt NICHT nach output/abschichtung_widmung_v2/distance_layers/ (das
# geteilte, read-only-symlinkte Checkpoint-Verzeichnis) - Ziel ist
# pipeline.contract.BUILD_LAYERS (build/layers/), privat in diesem Worktree.
# --source-dir (Default: output/abschichtung_widmung_v2/distance_layers)
# bleibt die einzige Lesequelle für die 8 externen Quell-Checkpoints aus
# W2.1/W2.3.

.PHONY: layer-geo
layer-geo:
	uv run python -m pipeline.layers.geo
