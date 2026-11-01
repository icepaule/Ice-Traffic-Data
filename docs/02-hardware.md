# 2 – Hardware

| Teil | Vorschlag | ca. Preis |
|---|---|---|
| ITS-G5-Empfänger | ESP32-C5-DevKitC-1 (N8R8), Platinenantenne | ~15 € |
| WLAN/MQTT-Brücke | Markenboard ESP32-C3 (z. B. DevKitM-1 oder WeAct C3FH4) | 10–15 € |
| Strom | KFZ-USB-Netzteil 5 V ≥ 2 A | 10–15 € |
| Kabel | USB-Datenkabel ×2, Jumper (Dupont) | 5–10 € |
| Gehäuse | 3D-Druck, Antennenbereich frei | 5–10 € |

Gesamt ca. **45–65 €**.

**Hinweise**
- Der Autor der Firmware berichtet, dass der **C3 Supermini sehr heiß** wird → im Auto lieber ein Markenboard.
- Bei den Alternativen zum Nachbau gibt es das Waveshare ESP32-C5-WIFI6-KIT (von V2X2MAP genutzt).
- Wichtig: Es muss der **ESP32-C5** sein; ESP32/S3/C3 können kein 5,9-GHz-802.11p.
