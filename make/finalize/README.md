# make/finalize/ — Konvention für die Finalisierungs-Stufe

Paket **W3.1** (`docs/rewrite/PLAN.md` §7) legt dieses Verzeichnis nach
demselben Muster wie `make/prep/` und `make/layers/` an (siehe deren
`README.md` - "nicht ähnlich, sondern dasselbe"). Der Auftrag für W3.1
verlangt ausdrücklich, dem `make/layers/README.md`-Muster zu folgen und
nicht davon abzuweichen; da die Finalisierung eine eigene Stufe ist (§3:
Roh → Prep → Layer → **Finalize** → verify), nicht Teil der Layer-Stufe,
bekommt sie ihr eigenes Verzeichnis statt eine vierte Datei unter
`make/layers/` zu werden - eine Datei dort würde automatisch Teil von
`LAYER_TARGETS` und würde `make -n layers` von drei auf vier Ziele
aufblähen, was die Abnahme dieses Pakets ausdrücklich als unverändert
verlangt ("`make -n layers` weiterhin alle drei").

## Ein Unterschied zu make/prep/ und make/layers/, ehrlich benannt

`Makefile` liest `make/prep/*.mk` und `make/layers/*.mk` bereits per
`-include` ein (siehe dortige Kommentare, `PREP_TARGETS`/`LAYER_TARGETS`).
Für `make/finalize/*.mk` gibt es **noch keine** entsprechende
`-include`-Zeile - der Auftrag für dieses Paket untersagt ausdrücklich,
`Makefile` anzufassen ("Fass Makefile nicht an"), und keines der bisher
verplanten Pakete (W3.2 Validierung, W4.3 Testverdrahtung - siehe
`docs/rewrite/PLAN.md` §7) trägt laut Plan die Verantwortung, diese eine
Zeile nachzutragen.

**Folge:** `finalize.mk` in diesem Verzeichnis ist heute noch nicht über
`make finalize` erreichbar. Der Zielname `finalize` und das darin
aufgerufene Modul (`python -m pipeline.finalize`) stehen aber bereits fest,
sodass ein künftiges Paket nur noch

    -include make/finalize/*.mk
    .PHONY: $(addprefix finalize-,$(basename $(notdir $(wildcard make/finalize/*.mk))))

(oder, da es hier nur eine Domäne gibt, schlicht `-include
make/finalize/*.mk` plus eine direkte Abhängigkeit von `finalize:` auf das
hier deklarierte `.PHONY`-Ziel) ins `Makefile` einfügen muss. Bis dahin:
direkt aufrufen mit `uv run python -m pipeline.finalize` bzw. `make -f
make/finalize/finalize.mk finalize`.

## Konvention (wie make/layers/README.md, § "Konvention")

- Das Ziel heißt `finalize` und steht in `make/finalize/finalize.mk` - sonst
  nirgends.
- Die 33 Checkpoint-Pfade, die `pipeline/finalize.py` liest, stehen in
  `pipeline/contract.py:LAYER_NAMES`/`LAYERS` (importiert, nicht neu
  erklärt); die vier Produktpfade in `pipeline/contract.py:PRODUCTS`.
- `.PHONY: finalize` steht in dieser eigenen Datei, nicht im
  Haupt-`Makefile`.
