# make/finalize/ — Konvention für die Finalisierungs-Stufe

Paket **W3.1** (`docs/rewrite/PLAN.md` §7) legt dieses Verzeichnis nach
demselben Muster wie `make/prep/` und `make/layers/` an (siehe deren
`README.md` - "nicht ähnlich, sondern dasselbe"). Der Auftrag für W3.1
verlangt ausdrücklich, dem `make/layers/README.md`-Muster zu folgen und
nicht davon abzuweichen; da die Finalisierung eine eigene Stufe ist (§3:
Roh → Prep → Layer → **Finalize** → Export - §3 nennt die fünfte Stufe
verify, bis W6.2 hiess sie so auch im Code), nicht Teil der Layer-Stufe,
bekommt sie ihr eigenes Verzeichnis statt eine vierte Datei unter
`make/layers/` zu werden - eine Datei dort würde automatisch Teil von
`LAYER_TARGETS` und würde `make -n layers` von drei auf vier Ziele
aufblähen, was die Abnahme dieses Pakets ausdrücklich als unverändert
verlangt ("`make -n layers` weiterhin alle drei").

## Ein Unterschied zu make/prep/ und make/layers/, der inzwischen geschlossen ist

`Makefile` liest `make/prep/*.mk` und `make/layers/*.mk` per `-include` ein
(siehe dortige Kommentare, `PREP_TARGETS`/`LAYER_TARGETS`). Für
`make/finalize/*.mk` fehlte diese Zeile eine Zeit lang - Paket W3.1 durfte
`Makefile` selbst ausdrücklich nicht anfassen ("Fass Makefile nicht an").
Seit **W3.2** steht `-include make/finalize/*.mk` im Haupt-`Makefile`
(siehe dortiger Kommentar bei "Vorpaket W3.1"): `finalize.mk` in diesem
Verzeichnis ist damit über `make finalize` erreichbar, direkt aufrufbar
wie jedes andere Ziel. Der frühere Umweg über `uv run python -m
pipeline.finalize` bzw. `make -f make/finalize/finalize.mk finalize`
bleibt weiterhin funktionsfähig, ist aber nicht mehr nötig.

## Konvention (wie make/layers/README.md, § "Konvention")

- Das Ziel heißt `finalize` und steht in `make/finalize/finalize.mk` - sonst
  nirgends.
- Die 33 Checkpoint-Pfade, die `pipeline/finalize.py` liest, stehen in
  `pipeline/contract.py:LAYER_NAMES`/`LAYERS` (importiert, nicht neu
  erklärt); die vier Produktpfade in `pipeline/contract.py:PRODUCTS`.
- `.PHONY: finalize` steht in dieser eigenen Datei, nicht im
  Haupt-`Makefile`.
