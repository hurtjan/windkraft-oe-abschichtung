# Offene Zahlen: bewusst als Klartext in `paper_vorlage.md`

Alle Ergebniszahlen, die das Zahlenregister (`tabellen/zahlen.json`) liefern kann, stehen als Platzhalter in der Vorlage. Diese Zahlen sind noch Klartext:

## (a) Anzahl der Eingabedatensätze (Regelentscheidung offen)
Keine TIF-Ergebnisse, sondern Zählungen der Rohdaten; Jan entscheidet, ob und wie sie in `make whitepaper` laufen.
- Abschnitt 3.1.2, Daten: DKM Gebäudegrundrisse (Code 41) rund 3,7 Mio., Gebäudenebenflächen (83) 0,34 Mio., Gärten (52) 2,3 Mio.
- Adressregister: 2 516 345 Adresspunkte; rund 2,52 Mio. Gebäudepunkte.
- Tabelle „Nutzungsarten im Adressregister“: Gebäude je Code 01 bis 09 (1 657 705; 635 146; 4 925; 39 684; 34 987; 33 759; 4 836; 83 687; 29 895).
- Abschnitt 3.2.1, Tabelle N1_natur_ebenen: UBA-Gebiete je Ebene (`uba_n_*`, Modul `natur_ebenen.py`) werden aus dem UBA-GeoPackage gezählt (nur gelesen). Läuft derzeit in `make whitepaper`, ist aber eine Zählung der Eingabedaten und damit eine Ausnahme von der TIF-only-Regel; Entscheidung Jan offen.

## (b) Haselbach-Beispiel (Abschnitt 3.1.2): erledigt
Zahlen kommen als `beispiel_haselbach.*` aus `beispiel_haselbach.json` ins Register (inkl. `wohnanteil_pct`).

## (c) Didaktisches Rechenbeispiel (Abschnitt 3.1.2)
„Zwölf Bauflächen, ein Wohnhaus, elf Lagerhallen, 8 %“: erfundenes Beispiel, keine Daten. Bleibt Klartext.

## Abschnitt 3.2.1 (Natur): erledigt
Text neu, Zahlen aus dem Register (`natur_amtlich_*`, `natur_osm_*`, `natur_osm_ausserhalb_amtlich_km2`).

## Weitere Klartext-Zahlen ohne Registerbezug
Parameter (750/25/150 m, 15°, 2 500 m, 150 W/m², 10 ha, 1 000/1 200 m, fünf Flächen, 100/200 m, 10 %) stehen in `config.json`; Rundungsangaben der Methodik (18 m, 35 m, rund 160 W/m²) sind Methodentext.
