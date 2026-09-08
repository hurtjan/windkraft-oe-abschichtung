"""Neuer Pipeline-Code (W0.2 ff.): contract, später prep/, layers/, finalize.py,
validate.py, export/ (bis W6.2: verify/ - siehe docs/rewrite/PLAN.md §3,
Verzeichnisbaum, dort noch unter dem alten Namen).

Absichtlich leer: dieses Paket importiert nichts aus ``calc`` oder
``scripts`` und wird selbst von beiden importiert. Ein Import hier würde
genau den Zyklus erzeugen, den ``pipeline.contract`` vermeiden soll.
"""
