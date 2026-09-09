# make/export/layer_md.mk — Paket W7.1 (Integration), Ersatz für Bahn 3s
# pipeline/export/layer_doc.py, das bewusst nicht gebaut wurde (siehe
# docs/rewrite/PLAN.md §7, Zeile W7.1/~~W7.2~~: "layer_doc.py liegt nicht
# auf dem kritischen Pfad: verzögert es, wird LAYER.md aus der Vorlage
# übernommen und der Generator als Registerpunkt notiert.").
#
# contract.PRODUCTS["layer_md"] (out/LAYER.md) braucht trotzdem ein
# Make-Ziel, sonst behauptet der Vertrag einen Erzeuger, den es nicht
# gibt. Bis pipeline/export/layer_doc.py existiert (echter Generator aus
# calc/band_manifest.py, Folge-TODO), kopiert dieses Ziel ehrlich die
# gepflegte Vorlage docs/layer.md nach out/LAYER.md - kein Vertrag, der
# mehr verspricht, als er hält.
#
# Siehe make/export/README.md für die Konvention (export-<domäne>, eigene
# Datei je Export-Paket, gelesen per -include make/export/*.mk im
# Haupt-Makefile).

.PHONY: export-layer_md
export-layer_md:
	@mkdir -p out
	cp docs/layer.md out/LAYER.md
