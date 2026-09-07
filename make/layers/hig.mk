# Paket W2.1 - siehe make/layers/README.md für die Konvention und
# pipeline/layers/hig.py für den Modul-Docstring (Umfang, Ein-/Ausgaben,
# Fingerabdruck-Konvention, Kopplung Widmung/Häuser-im-Grünen).
#
# Anders als W2.3/W2.4 kennt diese Stufe kein geteiltes, read-only
# Quell-Checkpoint-Verzeichnis - sie liest ausschließlich aus build/prep/
# (widmung/, kataster/, adressen/, noe_sekrop/) und schreibt ihre sieben
# eigenen Checkpoints nach pipeline.contract.BUILD_LAYERS (build/layers/),
# privat in diesem Worktree. Kein --force-layers berührt jemals
# output/abschichtung_widmung_v2/distance_layers/ (das geteilte
# Referenzverzeichnis) - dorthin schreibt dieses Ziel nie.

.PHONY: layer-hig
layer-hig:
	uv run python -m pipeline.layers.hig
