# 11 – Antennen (DigiKey-Recherche)

## Befund zum bestellten Board
Der **ESP32-C5-DevKitC-1-N8R8** trägt das Modul **ESP32-C5-WROOM-1** mit **Platinenantenne und ohne externen Anschluss** (Espressif-Benutzerhandbuch). Eine Zusatzantenne lässt sich daher nur durch Hardware-Umbau oder Boardtausch nutzen. Der **ESP32-C3-DevKitM-1** (WLAN 2,4 GHz zum Hotspot im Auto) braucht keine externe Antenne.

## Passende Antenne für ITS-G5 (5,9 GHz)
| Teil | Daten | Preis |
|---|---|---|
| Molex 2119960100 (DigiKey **WM26743-ND**) | flexible Klebe-Antenne 5,85–5,925 GHz, 5,5 dBi, U.FL/MHF1, 100 mm Kabel | 2,02 € netto / ca. 2,40 € brutto |

⚠ DigiKey nennt 17 Wochen Herstellervorlaufzeit trotz angezeigtem Lagerbestand – Verfügbarkeit vor der Bestellung prüfen. Die Antenne deckt **nur** 5,9 GHz ab, kein 2,4 GHz (dafür nicht nötig).

## Wie käme man an eine externe Antenne?
| Option | Bemerkung |
|---|---|
| Espressif ESP32-C5-WROOM-1U-N8R8 (nur Modul) | bei DigiKey gelistet, 20 Wochen Vorlaufzeit; Lötarbeit nötig |
| Waveshare ESP32-C5-WIFI6-KIT-N32R8-U | Board mit externer Antenne (nicht bei DigiKey gefunden) |
| DFRobot FireBeetle 2 ESP32-C5-U (N4) | WROOM-1U mit U.FL (nicht bei DigiKey gefunden) |

**Empfehlung:** Zuerst mit der Platinenantenne testen (so tun es auch die Projekte). Erst wenn die Reichweite im Auto nicht reicht, ein U.FL-Board plus Molex-Antenne nachrüsten – am besten innen an der Frontscheibe (nicht metallbedampfter Bereich). Eine Bohr-/Lötmodifikation am bestellten Board ist **nicht** empfohlen.

Die Messung „Pakete/min" im Dashboard erlaubt später einen A/B-Vergleich Platinen- vs. externe Antenne.
