<!-- GENERIERT aus docs/whitepaper/readme_vorlage.md durch make whitepaper — nicht von Hand ändern. -->
# Abschichtung Windkraft Österreich

Wo in Österreich könnte ein Windrad stehen? Dieses Repo beantwortet die Frage durch **Abschichtung**: Alle Flächen, auf denen Windkraft aus Gründen des Siedlungsschutzes, des Naturschutzes oder der Geografie ausscheidet, werden übereinandergelegt. Was übrig bleibt und zusammenhängend mindestens 10 ha groß ist, ist die Eignungsfläche. Das ist keine Standortprüfung und keine Genehmigungsgrundlage.

![Ausschlussflächen Mensch, Natur, Geografie und Eignungsfläche ≥ 10 ha](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/abb_methoden_uebersicht.png)

Ausführlich: **[Whitepaper](docs/whitepaper/paper.md)** (Methode, Daten, alle Kriterien).

## Ergebnis

Von 83 879 km² Landesfläche sind 95,6 % ausgeschlossen. Als Eignungsfläche ab 10 ha bleiben **3 177 km²**, das sind **3,8 %** der Landesfläche. 61 % davon liegen in Niederösterreich und im Burgenland.

**Ausschluss und Eignung je Bundesland** (in % der Landesfläche; „nur“ = durch keine andere Gruppe ausgeschlossen):

| Groesse (% des Landes) | Burgenland | Kärnten | Niederösterreich | Oberösterreich | Salzburg | Steiermark | Tirol | Vorarlberg | Wien | Österreich |
|---|---|---|---|---|---|---|---|---|---|---|
| Mensch | 69,6 | 69,1 | 84,6 | 83,6 | 49,2 | 66,7 | 38,7 | 56,7 | 94,4 | 67,8 |
| nur Mensch | 46,7 | 8,2 | 52,7 | 67,8 | 10,3 | 14,1 | 3,2 | 4,9 | 59,8 | 29,4 |
| Natur | 35,5 | 12,5 | 33,2 | 7,9 | 32,3 | 44,8 | 27,4 | 17,2 | 36,2 | 28,2 |
| nur Natur | 10,2 | 0,8 | 3,9 | 1,2 | 3,0 | 4,4 | 1,1 | 1,7 | 5,0 | 3,0 |
| Geografie | 6,2 | 87,4 | 16,3 | 25,7 | 82,3 | 69,7 | 92,9 | 89,5 | 6,9 | 55,1 |
| nur Geografie | 0,1 | 19,5 | 1,6 | 8,6 | 22,3 | 9,1 | 35,1 | 28,6 | 0,1 | 13,7 |
| Ausschluss gesamt | 83,5 | 96,7 | 93,1 | 96,4 | 97,0 | 97,8 | 97,5 | 96,9 | 99,9 | 95,6 |
| Eignung ≥ 10 ha | 16,4 | 2,5 | 6,7 | 3,1 | 2,0 | 1,6 | 1,4 | 1,9 | 0,0 | 3,8 |
| Eignung in km² | 651,6 | 237,7 | 1 290,9 | 371,3 | 142,3 | 259,6 | 173,9 | 49,2 | 0,2 | 3 176,6 |

*Quelle: Abschichtung, TIF sha256 58caa8ffa694…, Stand 2026-10-12. Bezugsflaeche: Summe der Bundesland-Masken (Zellmittelpunkt), 83 879,05 km².*

![Anteil der Ausschlussgruppen und der Eignungsfläche je Bundesland](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/abb2_balken.png)

**Wald und landwirtschaftliche Flächen** (Kataster; zum Vergleich, kein Ausschluss). *Bestand* = amtliche Windkraftzonen der Länder und bestehende Windparks außerhalb dieser Zonen (Hülle um die Windräder plus 200 m); *Potentialfläche* = Eignungsfläche ab 10 ha, soweit sie nicht schon Bestand ist; *C48* = Äcker, Wiesen, Weiden.

| Land | Landesfläche | Wald | C48 | Bestand | Wald | C48 | Potentialfläche | Wald | C48 |
|---|---|---|---|---|---|---|---|---|---|
| Österreich | 83 879,1 (100,0 %) | 36 460,8 (43 %) | 23 541,9 (28 %) | 541,2 (0,6 %) | 134,8 (25 %) | 348,1 (64 %) | 2 808,3 (3,3 %) | 1 477,3 (53 %) | 775,7 (28 %) |
| Niederösterreich | 19 186,0 (100,0 %) | 6 883,0 (36 %) | 8 667,3 (45 %) | 319,1 (1,7 %) | 62,5 (20 %) | 229,3 (72 %) | 1 058,7 (5,5 %) | 434,0 (41 %) | 508,6 (48 %) |
| Steiermark | 16 402,7 (100,0 %) | 9 495,8 (58 %) | 3 521,7 (21 %) | 51,1 (0,3 %) | 38,8 (76 %) | 0,7 (1 %) | 245,5 (1,5 %) | 200,1 (82 %) | 7,6 (3 %) |
| Tirol | 12 640,1 (100,0 %) | 5 037,4 (40 %) | 994,1 (8 %) | 0,1 (0,00 %) | 0,0 (–) | 0,0 (–) | 173,9 (1,4 %) | 54,9 (32 %) | 1,0 (1 %) |
| Oberösterreich | 11 978,4 (100,0 %) | 4 728,9 (39 %) | 5 408,9 (45 %) | 5,9 (0,05 %) | 4,2 (72 %) | 1,5 (26 %) | 367,6 (3,1 %) | 326,0 (89 %) | 14,4 (4 %) |
| Kärnten | 9 538,0 (100,0 %) | 5 193,3 (54 %) | 1 673,2 (18 %) | 8,3 (0,09 %) | 6,9 (84 %) | 0,0 (0 %) | 230,7 (2,4 %) | 116,7 (51 %) | 0,4 (0 %) |
| Salzburg | 7 155,9 (100,0 %) | 2 893,3 (40 %) | 985,9 (14 %) | 18,0 (0,3 %) | 13,1 (73 %) | 0,0 (0 %) | 137,0 (1,9 %) | 74,0 (54 %) | 0,9 (1 %) |
| Burgenland | 3 961,9 (100,0 %) | 1 218,8 (31 %) | 1 841,8 (46 %) | 137,7 (3,5 %) | 9,2 (7 %) | 115,9 (84 %) | 545,6 (13,8 %) | 262,5 (48 %) | 241,8 (44 %) |
| Vorarlberg | 2 601,4 (100,0 %) | 931,3 (36 %) | 399,1 (15 %) | 0,0 (0,0 %) | 0,0 (–) | 0,0 (–) | 49,2 (1,9 %) | 9,0 (18 %) | 0,8 (2 %) |
| Wien | 414,7 (100,0 %) | 79,0 (19 %) | 49,8 (12 %) | 1,1 (0,3 %) | 0,1 (5 %) | 0,7 (67 %) | 0,2 (0,04 %) | 0,0 (–) | 0,2 (–) |

*Quelle: Abschichtung, TIF sha256 58caa8ffa694…, Analyse-Raster sha256 89b89f1fb666…, Stand 2026-10-12.*

Bestand = amtliche Windzonen (`official_wind_zoning`) oder Bestandsanlagen außerhalb der Zonen (`wka_bestand_ausserhalb_zonen`); Potentialfläche = Eignung ≥ 10 ha (`available_cleaned_min_10ha`) ohne Bestand. Prozent bei Landesfläche, Bestand und Potentialfläche: Anteil an der Landesfläche; bei Wald und C48: Anteil der links stehenden Fläche ("–" bei Bezugsfläche < 0,5 km²).

Wald = Kataster-Nutzungscodes 56 und 55 (`kataster_wald`); C48 = Kataster-Code 48, Äcker, Wiesen, Weiden (`kataster_aecker_wiesen_weiden`); Flächen in km² (Zelle 0,000625 km²).

## Kriterien

| Gruppe | Kriterium | Regel | Quelle |
| --- | --- | --- | --- |
| Mensch | Siedlung | 1 000 m Abstand zu gewidmetem Wohnbauland (NÖ 1 200 m) | Flächenwidmung der Länder |
| Mensch | Häuser im Grünen | 750 m Abstand zu Sonderwidmungen und erkannten Streusiedlungen | Flächenwidmung, Kataster, Adressregister, NÖ-Mindestabstandszonen |
| Mensch | Gebäude | 25 m Abstand (Seilbahnstationen 50 m) | Kataster, OpenStreetMap |
| Mensch | Verkehr | 150 m zu höherrangigen Straßen, Hauptbahnen, Personenseilbahnen | OpenStreetMap |
| Mensch | Militär | ohne Abstand | OpenStreetMap |
| Mensch | Luftfahrt | Areal der sechs Verkehrsflughäfen und Anflugkorridore | OpenStreetMap |
| Natur | Schutzgebiete | per Verordnung oder Bescheid geschützt, ohne Abstand | Umweltbundesamt |
| Geografie | Hangneigung | steiler als 15° | Höhenraster 25 m (BEV) |
| Geografie | Seehöhe | über 2 500 m | Höhenraster 25 m (BEV) |
| Geografie | Wind | unter 150 W/m² in 130 m Höhe | Global Wind Atlas |
| Geografie | Gewässer | ab 1 ha | OpenStreetMap |

Gerechnet wird auf einem Raster von 25 × 25 m (EPSG:31287); Abstände sind Kreise um jede betroffene Zelle.

## Produkte

- `out/abschichtung.tif`: **45 Bänder**, 25 m, EPSG:31287, `uint8`; jedes Kriterium als eigene Maske, dazu Summen je Gruppe und die Eignungsfläche. Manifest `out/abschichtung.bands.json`, Schema **2.3.0**, TIF-sha256 `58caa8ffa694…`. TIF und Manifest nur zusammen weitergeben; Vertrag für Weiterverarbeiter: [`docs/HANDOFF.md`](docs/HANDOFF.md).
- `out/abschichtung_analyse.tif`: gleiches Raster, Landnutzungsklassen aus dem Kataster (Wald, Äcker/Wiesen/Weiden u. a.); nur für Auswertungen.

Die Ausgaben liegen nicht im Repo (`out/` ist gitignored). Abbildungen hängen am Release [`abbildungen-latest`](https://github.com/hurtjan/windkraft-oe-abschichtung/releases/tag/abbildungen-latest).

## Ausführen

Voraussetzungen: Python mit [uv](https://docs.astral.sh/uv/), `osmium-tool` (`brew install osmium-tool`), rund 25 GB Plattenplatz; zum Veröffentlichen der Abbildungen die GitHub-CLI `gh`.

```bash
uv sync                # Abhängigkeiten
# Rohdaten nach data/ — siehe docs/rohdaten.md
make check-guards      # Wächter: data/ wird nur gelesen
make                   # prep → layers → finalize → analyse-raster → export
make test
make bilanz            # Flächenbilanz je Bundesland (docs/flaechenbilanz.tsv)
make whitepaper        # Zahlen, Tabellen, Abbildungen; erzeugt paper.md und diese README
make abb-publish       # Probelauf; mit CONFIRM=1 werden die Abbildungen hochgeladen
```

Ein Kaltstart dauert deutlich über eine Stunde; allein die Kataster-Aufbereitung braucht 45–70 Minuten. Unvollständige Rohdaten führen **nicht** zum Abbruch, sondern zu einem plausibel aussehenden, aber falschen Ergebnis — vorher [`docs/rohdaten.md`](docs/rohdaten.md), Abschnitt 0, lesen.

Diese README und das Whitepaper werden von `make whitepaper` aus [`docs/whitepaper/readme_vorlage.md`](docs/whitepaper/readme_vorlage.md) und [`docs/whitepaper/paper_vorlage.md`](docs/whitepaper/paper_vorlage.md) erzeugt; Änderungen gehören in die Vorlagen.

## Dokumentation

- [`docs/whitepaper/paper.md`](docs/whitepaper/paper.md): Whitepaper
- [`docs/BETRIEB.md`](docs/BETRIEB.md): Kette im Detail, Wiederholbarkeit, Tests
- [`docs/HANDOFF.md`](docs/HANDOFF.md): Vertrag für alle, die das GeoTIFF weiterverarbeiten
- [`docs/LAYER-MANIFEST.md`](docs/LAYER-MANIFEST.md): Bänder und Manifest
- [`docs/rohdaten.md`](docs/rohdaten.md): Herkunft und Lizenz jeder Eingangsdatei
- [`docs/whitepaper/README.md`](docs/whitepaper/README.md): Whitepaper-Erzeugung und Abbildungs-Veröffentlichung
- [`docs/dataflow/`](docs/dataflow/): Datenfluss-Diagramm

## Datenquellen und deren Lizenzen

Die Rohdaten sind nicht Teil des Repos und behalten ihre eigenen Bedingungen (Details und Bezugswege: [`docs/rohdaten.md`](docs/rohdaten.md)):

- OpenStreetMap (Geofabrik-Extrakt): ODbL 1.0, © OpenStreetMap-Mitwirkende
- BEV (Adressregister, Digitale Katastralmappe, Verwaltungsgrenzen, Geländemodell): CC BY 4.0, soweit dort ausgewiesen
- Flächenwidmung der neun Länder: je Land eigene Bedingungen (OÖ und Tirol CC BY 4.0); siehe `docs/rohdaten.md`
- Schutzgebiete: Umweltbundesamt (SG_AT_2024)
- NÖ SekROP Windkraft: Land Niederösterreich
- Global Wind Atlas: Zitat und Bedingungen wie in `docs/rohdaten.md` und im Whitepaper (Davis et al. 2023)

## Lizenz

Code: MIT ([`LICENSE`](LICENSE)). Texte, Dokumentation und Abbildungen: CC BY 4.0 ([`LICENSE-docs`](LICENSE-docs)), © 2026 Jan Hurt.
