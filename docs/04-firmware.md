# 4 – Firmware bauen & flashen

Basis: [bertrik/its-g5-receiver](https://github.com/bertrik/its-g5-receiver) (gepinnter Stand `45db567`). Wir ergänzen einen kleinen Patch für das ESP32-C3-DevKitM-1 (UART1 auf GPIO4).

**Status:** Beide Firmwares wurden hier erfolgreich **gebaut** (C5 `devkitc1-n4`, C3 `devkitm1`). Geflasht/getestet ist noch nichts – die Boards sind noch nicht da.

```bash
cd firmware
./build.sh                          # klont Upstream, wendet Patch an, baut beide
./build.sh flash-c5 /dev/ttyACM0    # nur C5 per USB, 5-V-Brücke ab
./build.sh flash-c3 /dev/ttyUSB0    # nur C3 per USB (uploadfs + upload)
```
`build.sh` installiert bei Bedarf PlatformIO. Der erste Build lädt Toolchains (C5 ca. 4 min, C3 ca. 1,5 min).

## Schreibtischtest
1. **C5 allein:** `pio device monitor` → Kommandozeile; LED blinkt jede Sekunde (aktiv), grün bei Paket. Pakete erscheinen als Hexdump.
2. Hexdump in Wireshark: `text2pcap -l 105 message.txt message.pcap && wireshark message.pcap`
3. **C3 allein:** `pio device monitor`, dann WLAN setzen: `wifi <ssid> <passwort>` (wird im NVS gespeichert). `wifi` zeigt die IP der Konfigurationsseite.
4. Beide verbinden. Am Schreibtisch kommen evtl. keine Pakete – das ist normal.

## Lokale Webseite des C3 (Zusatz)
Die Bridge-Firmware bringt bereits eine **Weboberfläche** mit (http://its-g5-bridge.local bzw. IP): Status, Statistik und MQTT-Konfiguration. Das ist der Konfigurationsweg und eine einfache lokale Anzeige. Ein **eigener Live-Ampel-Screen direkt auf dem C3** wäre eine spätere Erweiterung (siehe [Offene Punkte](07-offene-punkte.md)); die Dekodierung läuft bewusst auf dem Heimserver ([Decoder](09-decoder.md)).
