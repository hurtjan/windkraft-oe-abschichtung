# make/export/layer_manifest_md.mk — Paket W7.6.
#
# docs/LAYER-MANIFEST.md ist der Vertrag, WIE das Bänder-Manifest zu lesen
# ist (Regeln, Feldtabelle, Invarianten) - anders als docs/layer.md
# (Bandwerte, jetzt aus pipeline/export/layer_doc.py erzeugt) enthält diese
# Datei keine aus dem Manifest ableitbaren Werte, sondern von Hand
# geschriebene/geprüfte Regeltexte. Ein echtes Kopierziel ist hier deshalb
# richtig, kein Generator - siehe docs/LAYER-MANIFEST.md selbst für die
# Herkunft und die W7.6-Korrekturen.
#
# contract.PRODUCTS["layer_manifest_md"] (out/LAYER-MANIFEST.md) ist das
# siebte Endprodukt (docs/rewrite/PLAN.md, Paket W7.6).
#
# Siehe make/export/README.md für die Konvention (export-<domäne>, eigene
# Datei je Export-Paket, gelesen per -include make/export/*.mk im
# Haupt-Makefile).

.PHONY: export-layer_manifest_md
export-layer_manifest_md:
	@mkdir -p out
	cp docs/LAYER-MANIFEST.md out/LAYER-MANIFEST.md
