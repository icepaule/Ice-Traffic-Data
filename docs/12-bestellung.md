# 12 – Bestellliste DigiKey

Stand der Preise/Bestände: 01.11.2026 (DigiKey.de-Produktseiten, vor Bestellung erneut prüfen).

## Bereits bestellt
| DigiKey-Nr. | Teil |
|---|---|
| 1965-ESP32-C5-DEVKITC-1-N8R8-ND | ITS-G5-Sniffer (PCB-Antenne) |
| 1965-ESP32-C3-DEVKITM-1-N4X-ND | WLAN/MQTT-Brücke |

## Ergänzung: LoRa-Auto-Knoten
| # | DigiKey-Nr. | Teil | Preis netto / brutto | Bestand |
|---|---|---|---|---|
| 1 | 1597-102010611-ND | Seeed XIAO ESP32S3 + Wio-SX1262 („Meshtastic & LoRa") | 9,68 € / 11,52 € | 409 (4 Wochen Lieferzeit) |
| 2 | ANT-868-PW-QW-UFL-ND | Linx-868-MHz-Antenne, U.FL, 216 mm Kabel, 1,6 dBi | 11,01 € / 13,10 € | 684 |
| 3 | 1597-109020022-ND | Seeed Grove GPS (Air530) | 9,76 € | 797 |

Summe ca. 35–37 € brutto.

## Bewusst nicht bestellt
- Seeed-Antenne 318020389: für 902–928 MHz ausgelegt, nicht für EU868.
- Seeed-Antenne 318020269 (868 MHz): zum Recherchezeitpunkt nicht lieferbar.
- Molex 2119960100 (ITS-G5, 5,9 GHz): das bestellte C5-Board hat keinen U.FL-Anschluss, DigiKey führt kein C5-Kit mit U.FL → siehe [11](11-antennen.md).

## Zu klären nach Lieferung
- Liegen dem Kit Antennen bei? (Seeed-Wiki: ja, DigiKey-Seite listet nur „Board(s)".)
- Liegt dem Grove-GPS ein Grove-Kabel bei? Sonst Jumper.
- UART-Pins am XIAO ESP32S3 (D6/D7 = GPIO43/44?) und Belegung unter dem Wio-Aufsatz gegen das Datenblatt prüfen.
