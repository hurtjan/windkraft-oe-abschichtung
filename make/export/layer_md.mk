# make/export/layer_md.mk — Paket W7.6: Ersatz des Kopierziels durch den
# echten Generator pipeline/export/layer_doc.py.
#
# Bis W7.6 kopierte dieses Ziel ehrlich die von Hand gepflegte Vorlage
# docs/layer.md nach out/LAYER.md (siehe Git-Historie dieser Datei) - ein
# Notbehelf aus W7.1, dort dokumentiert als "Registerpunkt 66: layer_doc.py
# fehlt noch". Der Notbehelf ist inzwischen selbst zum Risiko geworden: ein
# Kopierziel schreibt bei jedem Lauf einen frischen Zeitstempel auf einen
# Inhalt, der beim nächsten Bandwechsel nicht mehr mitzieht, ohne dass es
# auffällt (34 von 40 Bandnamen waren zum Zeitpunkt des Fundes bereits
# veraltet). contract.PRODUCTS["layer_md"] (out/LAYER.md) wird deshalb ab
# hier vom Generator erzeugt, der ausschließlich aus
# out/abschichtung.bands.json liest - kein Bandname im Code, siehe
# pipeline/export/layer_doc.py.
#
# Siehe make/export/README.md für die Konvention (export-<domäne>, eigene
# Datei je Export-Paket, gelesen per -include make/export/*.mk im
# Haupt-Makefile).

.PHONY: export-layer_md
export-layer_md:
	@mkdir -p out
	uv run python -m pipeline.export.layer_doc
