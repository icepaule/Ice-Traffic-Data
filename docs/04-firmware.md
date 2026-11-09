# 4 – Firmware bauen & flashen

Basis: [bertrik/its-g5-receiver](https://github.com/bertrik/its-g5-receiver) (gepinnter Stand `45db567`). Wir ergänzen zwei Patches: `0001` für das ESP32-C3-DevKitM-1 (UART1 auf GPIO4) und `0002` (Format **ITS6** mit RSSI/Rauschpegel/Rate, Zähler für Fehler-, Unicast- und verworfene Pakete, **921 600 Baud**; Details und Begründung in [22](22-plan-verbesserungen.md)). Der Rückfall auf 115 200 Baud geht mit `-DITS_BAUD=115200` in **allen drei** Firmwares.

**Status:** Beide Firmwares wurden hier erfolgreich **gebaut** (C5 `devkitc1-n4`, C3 `devkitm1`). Geflasht/getestet ist noch nichts – die Boards sind noch nicht da.

```bash
cd firmware
./build.sh                          # klont Upstream, wendet Patch 0001 bis 0005 an, baut beide
./build.sh flash-c5 /dev/ttyACM0    # nur C5 per USB, 5-V-Brücke ab
./build.sh flash-c3 /dev/ttyUSB0    # nur C3 per USB (uploadfs + upload)
```
`build.sh` installiert bei Bedarf PlatformIO. Es prüft bei jedem Lauf den Stand von `src/` (Marker `send_its6`) und zieht fehlende Patches nach; ein nur mit 0001 gepatchtes, älteres `src/` wird so auf 0002 gebracht. Der Port `/dev/ttyUSB0` ist ein Beispiel: mit `ls -l /dev/serial/by-id/` den richtigen suchen (am Entwicklungsrechner war `ttyUSB0` ein Zigbee-Dongle, die C3 hing an `ttyUSB1`). Nach dem Flashen beim C5 `stats` im Shell-Prompt eingeben: `baud=921600` zeigt, dass Patch 0002 drauf ist. Der erste Build lädt Toolchains (C5 ca. 4 min, C3 ca. 1,5 min).

## Schreibtischtest
1. **C5 allein:** `pio device monitor` → Kommandozeile; LED blinkt jede Sekunde (aktiv), grün bei Paket. Pakete erscheinen als Hexdump.
2. Hexdump in Wireshark: `text2pcap -l 105 message.txt message.pcap && wireshark message.pcap`
3. **C3 allein:** `pio device monitor`, dann WLAN setzen: `wifi <ssid> <passwort>` (wird im NVS gespeichert). `wifi` zeigt die IP der Konfigurationsseite.
4. Beide verbinden. Am Schreibtisch kommen evtl. keine Pakete – das ist normal.

## Lokale Webseite des C3 (Zusatz)
Die Bridge-Firmware bringt bereits eine **Weboberfläche** mit (http://its-g5-bridge.local bzw. IP): Status, Statistik und MQTT-Konfiguration. Das ist der Konfigurationsweg und eine einfache lokale Anzeige. Ein **eigener Live-Ampel-Screen direkt auf dem C3** wäre eine spätere Erweiterung (siehe [Offene Punkte](07-offene-punkte.md)); die Dekodierung läuft bewusst auf dem Heimserver ([Decoder](09-decoder.md)).

**Patches:** 0001 DevKitM-1/UART1, 0002 ITS6 (RSSI, Zähler, Baudrate), 0003 C3-Schleife leert den UART-Puffer, 0004 C3 meldet Sniffer-Zähler und Feldstärke per MQTT (`its/<id>/stats`), 0005 eigene Partitionstabelle für die C3 (App-Slot 1,9 MB). Wegen 0005 ändert sich der Platz des Dateisystems; Firmware und Dateisystem müssen immer zusammen geflasht werden (`build.sh flash-c3` macht das). **Danach die MQTT-Einstellungen der C3 neu setzen.**
