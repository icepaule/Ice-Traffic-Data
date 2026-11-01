# 7 – Offene Punkte & Ausbau

- [ ] Hardware bestellen (siehe [02](02-hardware.md))
- [ ] Firmware-Details (Environments, Pins) aus Repo verifizieren
- [ ] Gibt es SPATEM/MAPEM im Raum München/Ottobrunn tatsächlich über ITS-G5?
- [ ] OpenTrafficMap: Node-Registrierung/Self-Service-Portal prüfen (auf der Wiki-Startseite nicht beschrieben)
- [ ] UART 115200 Baud begrenzt (~11,5 kB/s): höhere Baudrate, größere Puffer, Drop-Zähler
- [ ] iPhone-Position für „Fahrzeug vor/hinter mir" einbeziehen (C5 hat kein GNSS)

## Ausbau: eigenes Labor ohne Cloud
```mermaid
flowchart LR
    C3[ESP32-C3] -- MQTT --> B[Eigener Mosquitto]
    B --> D[Decoder SPATEM/MAPEM/CAM/DENM]
    D --> G[Dashboard / Karte]
```
Alternativ: ESP32-S3-Touchdisplay als Fahrzeugdisplay (iOS hat keine fertige App; V2X2MAP/CITS-to-go sind Android).
