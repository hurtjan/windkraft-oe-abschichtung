# Abschichtung Windkraft Österreich

Wo in Österreich könnte ein Windrad stehen? Dieses Repo beantwortet die
Frage durch **Abschichtung**: Von der Landesfläche werden nacheinander alle
Flächen abgezogen, auf denen Windkraft aus Gründen des Siedlungsschutzes,
des Naturschutzes oder der Geografie ausscheidet — Wohngebiete samt
Abstandspuffer, Schutzgebiete, steiles oder zu hoch gelegenes Gelände,
windschwache Lagen. Was übrig bleibt (zusammenhängend mindestens 10 ha), ist
die Eignungs- bzw. Potentialfläche. Es ist keine Standortprüfung und keine
Genehmigungsgrundlage.

![Anteil der Ausschlussgruppen und der Eignungsfläche je Bundesland](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/abb2_balken.png)

## Whitepaper in Kürze

Zahlen wörtlich aus `docs/whitepaper/paper.md` (erzeugt mit `make whitepaper`).

- Ein bundesweit einheitliches Kriterienset in drei Gruppen: Mensch, Natur, Geografie.
- Rechenbasis: Raster mit 25 × 25 m (EPSG:31287); Abstände als Kreise um betroffene Zellen.
- Siedlung: 1 000 m Abstand zu gewidmetem Wohnbauland, in Niederösterreich 1 200 m.
- Häuser im Grünen: 750 m; Streusiedlungen werden aus Kataster und Adressregister erkannt (10 852 Gruppen außerhalb Niederösterreichs).
- Ohne Streusiedlungs-Erkennung wäre die Eignungsfläche ab 10 ha um 709 km² (+22 %) größer.
- Häuser im Grünen gesamt, mit Abstand: 40 744 km².
- Natur: amtliche Schutzgebiete des Umweltbundesamts, 23 648 km² oder 28,2 % des Staatsgebiets.
- Geografie: Hangneigung über 15°, Seehöhe über 2 500 m, Wind unter 150 W/m², Gewässer ab 1 ha.
- Landesfläche Österreich: 83 879,1 km²; Wald 36 460,8 km² (43 %), Äcker, Wiesen, Weiden 23 541,9 km² (28 %).
- Potentialfläche (Eignung ≥ 10 ha ohne Bestand): 2 808,3 km² (3,3 % der Landesfläche), davon Wald 1 477,3 km² (53 %).
- Bestand (Windkraftzonen und Bestandsanlagen außerhalb): 541,2 km² (0,6 %).

## Produkt

`out/abschichtung.tif`: **45 Bänder**, 25 m, EPSG:31287, `uint8`; jedes
Ausschlusskriterium als eigene Maske, dazu Summen je Familie und die
bereinigte Potentialfläche. Manifest `out/abschichtung.bands.json`, Schema
**2.3.0**; aktueller sha256-Präfix `58caa8ff`. TIF und Manifest nur zusammen
weitergeben. Die Ausgaben liegen nicht im Repo (`out/` ist gitignored).

## Zum Laufen bringen

Voraussetzungen: Python ≥ 3.10 mit [uv](https://docs.astral.sh/uv/),
`osmium-tool` (`brew install osmium-tool`), rund 25 GB Plattenplatz.

```bash
uv sync                # Abhängigkeiten
# Rohdaten nach data/ — siehe docs/rohdaten.md
make check-guards      # Wächter: data/ wird nur gelesen
make                   # prep → layers → finalize → analyse-raster → export
make test
make whitepaper        # Tabellen und Abbildungen, nur aus dem TIF
make analyse-raster    # zweites Produkt out/abschichtung_analyse.tif
make abb-publish       # Trockenlauf; make abb-publish CONFIRM=1 veröffentlicht
```

Ein Kaltstart dauert rund eine Stunde. Unvollständige Rohdaten führen
**nicht** zum Abbruch, sondern zu einem plausibel aussehenden, aber falschen
Ergebnis — vorher `docs/rohdaten.md`, Abschnitt 0, lesen.

## Dokumentation

- [`docs/BETRIEB.md`](docs/BETRIEB.md) — Kette im Detail, Wiederholbarkeit, Tests
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — Vertrag für alle, die das GeoTIFF weiterverarbeiten
- [`docs/LAYER-MANIFEST.md`](docs/LAYER-MANIFEST.md) — Bänder und Manifest
- [`docs/rohdaten.md`](docs/rohdaten.md) — Herkunft und Lizenz jeder Eingangsdatei
- [`docs/whitepaper/README.md`](docs/whitepaper/README.md) — Whitepaper und Abbildungs-Veröffentlichung
- [`docs/dataflow/`](docs/dataflow/) — Datenfluss-Diagramm

## Datenquellen und deren Lizenzen

Die Rohdaten sind nicht Teil des Repos und behalten ihre eigenen Bedingungen
(Details und Bezugswege: [`docs/rohdaten.md`](docs/rohdaten.md)):

- OpenStreetMap (Geofabrik-Extrakt): ODbL 1.0, © OpenStreetMap-Mitwirkende
- BEV (Adressregister, Digitale Katastralmappe, Verwaltungsgrenzen, Geländemodell): CC BY 4.0, soweit dort ausgewiesen
- Flächenwidmung der neun Länder: je Land eigene Bedingungen (OÖ und Tirol CC BY 4.0); Lage siehe `docs/rohdaten.md`
- Schutzgebiete: Umweltbundesamt (SG_AT_2024)
- NÖ SekROP Windkraft: Land Niederösterreich
- Global Wind Atlas: Zitat und Bedingungen wie in `docs/rohdaten.md` und im Whitepaper (Davis et al. 2023)

## Lizenz

Code: MIT ([`LICENSE`](LICENSE)). Texte, Dokumentation und Abbildungen:
CC BY 4.0 ([`LICENSE-docs`](LICENSE-docs)), © 2026 Jan Hurt.
