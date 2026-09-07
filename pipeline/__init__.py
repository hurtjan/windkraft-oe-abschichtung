"""Neuer Pipeline-Code (W0.2 ff.): contract, später prep/, layers/, finalize.py,
validate.py, verify/ (siehe docs/rewrite/PLAN.md §3, Verzeichnisbaum).

Absichtlich leer: dieses Paket importiert nichts aus ``windkraft`` oder
``scripts`` und wird selbst von beiden importiert. Ein Import hier würde
genau den Zyklus erzeugen, den ``pipeline.contract`` vermeiden soll.
"""
