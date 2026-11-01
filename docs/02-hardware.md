# 2 – Hardware & Einkaufsliste (DigiKey)

## Bestellt

| DigiKey-Nr. | Teil | Aufgabe |
|---|---|---|
| 1965-ESP32-C5-DEVKITC-1-N8R8-ND | Espressif ESP32-C5-DevKitC-1-N8R8 (Modul ESP32-C5-WROOM-1, **PCB-Antenne**) | ITS-G5-Sniffer |
| 1965-ESP32-C3-DEVKITM-1-N4X-ND | Espressif ESP32-C3-DevKitM-1-N4X (ESP32-C3-MINI-1) | WLAN/MQTT-Brücke + lokale Webseite |

## Zusätzlich nötig (nicht bestellt)

| Teil | Hinweis | ca. |
|---|---|---|
| KFZ-USB-Netzteil 5 V ≥ 2 A | möglichst mit Überspannungsschutz | 10 € |
| 2× USB-Datenkabel (USB-C für C5, Micro-USB für C3) | beim Flashen beide Boards einzeln anschließen | 5 € |
| Dupont-Jumper (3 Stück) | siehe [Verdrahtung](03-verdrahtung.md) | 2 € |
| Gehäuse (3D-Druck) | Antennenbereich des C5 frei lassen, nicht neben Metall | Material |

## Antennen

Siehe [11 – Antennen](11-antennen.md). Kurzfassung: **Das bestellte C5-Board hat keinen U.FL-Anschluss** – eine externe Antenne ist ohne Boardwechsel nicht möglich. Zuerst mit der Platinenantenne testen.

## Wichtig
- Es muss ein **ESP32-C5** sein; ESP32/S2/S3/C3 können kein 5,9-GHz-802.11p.
- Die Firmware-Env des Upstream-Projekts (`devkitc1-n4`) läuft auf dem N8R8, nutzt aber nur 4 MB Flash und kein PSRAM – das genügt.
