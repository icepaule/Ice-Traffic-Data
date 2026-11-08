# Ergebnisse der ersten Testfahrt (08.11.2026)

Bereinigte Daten und Auswertung. **Alle Daten im Umkreis von 5 km um Start und Ziel sind entfernt.** Die Originaldaten bleiben privat.

| Datei | Inhalt |
|---|---|
| `daten/log_bereinigt.csv` | Zähler je 10 s mit GPS (Spalten: `utc, uptime_s, fix, lat, lon, kmh, sats, cam, denm, spatem, mapem, signiert, sonstige`; Zählung der **alten** Firmware) |
| `daten/frames_bereinigt.bin` | Rohpakete im ITS5-Format (`ITS5` + Sekunden + µs + Länge + 802.11-Rahmen), abspielbar im Decoder |
| `daten/frames_bereinigt.pcap` | dieselben Pakete für Wireshark/tshark (LINKTYPE 105, 802.11) |
| `empfang_timeline.csv` | 132 Empfangsfenster: Zeit, Position, Tempo, Paketzahlen, Straße, Hausnummer (nur wenn OSM sie liefert), Ortsteil, Ort, PLZ |
| `empfang_abschnitte.csv` | 23 zusammenhängende Empfangsabschnitte |
| `denm_ereignisse.json` | Gefahrenmeldungen mit Adresse |

Hinweis: Die Pakete enthalten unverschlüsselt ausgesendete Kennungen und Positionen **anderer Verkehrsteilnehmer** (Pseudonyme, wochenweise wechselnd).

Auswertung: [`docs/20-auswertung-testfahrt-1.md`](../../docs/20-auswertung-testfahrt-1.md) und [`docs/21-testfahrt-1-timeline-karte-verbesserungen.md`](../../docs/21-testfahrt-1-timeline-karte-verbesserungen.md). Erzeugt mit `scripts/auswertung_fahrt.py` und `scripts/ergebnisse_testfahrt.py`.

Kartendaten und Adressen: © OpenStreetMap-Mitwirkende, ODbL (https://www.openstreetmap.org/copyright).
