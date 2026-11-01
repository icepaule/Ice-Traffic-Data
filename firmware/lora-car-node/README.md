# LoRa-Auto-Knoten (ENTWURF)

> **Status: Entwurf.** Kompiliert (PlatformIO), Logik per PC-Test geprüft, **noch nicht auf Hardware getestet** (Boards bestellt). Pins aus der Meshtastic-Variante `seeed_xiao_s3` übernommen – nach Lieferung gegen das Datenblatt prüfen.

Seeed **XIAO ESP32S3 + Wio-SX1262** hört parallel am TX-Draht des ESP32-C5 mit, zählt CAM/DENM/SPATEM/MAPEM, liest das **Grove GPS (Air530)** und sendet alle 60 s (sowie bei neuer Gefahrenmeldung frühestens nach 30 s) eine **25-Byte-Zusammenfassung** per LoRaWAN (ABP, 868,1 MHz, DR3) an das Heim-Einkanal-Gateway → ChirpStack → Home Assistant.

## Verdrahtung
| XIAO ESP32S3 | Gegenstelle |
|---|---|
| D7 = GPIO44 (RX1) | TX (GPIO11) des ESP32-C5, nur Mithören, 3,3 V |
| D5 = GPIO6 | TX des Grove-GPS |
| D4 = GPIO5 | RX des Grove-GPS |
| 5 V / GND | wie die übrigen Boards (KFZ-Netzteil) |
| U.FL | 868-MHz-Antenne (Linx ANT-868-PW-QW-UFL) – **nie ohne Antenne senden** |

SX1262 (fest auf dem Wio-Aufsatz): NSS 41, DIO1 39, BUSY 40, RESET 42, SCK 7, MISO 8, MOSI 9, RXEN 38, TCXO 1,8 V an DIO3, DIO2 als HF-Schalter.

## Bauen
```bash
# 1) Gerät in ChirpStack anlegen und secrets.h erzeugen (auf dem ChirpStack-Host, Schlüssel bleiben lokal):
sudo python3 scripts/provision-chirpstack.py /opt/chirpstack
# 2) Bauen und flashen
cd firmware/lora-car-node && pio run -t upload
# Tests ohne Hardware
pio test -e native && node test/codec.test.js
```
Ohne gültige `secrets.h` (DevAddr 0) startet der Knoten im Nur-Seriell-Modus und sendet **nicht**.

## Ende-zu-Ende ohne Hardware getestet
`scripts/simulate-uplink.py` baut mit den echten ABP-Schlüsseln ein gültiges LoRaWAN-Paket (AES-Verschlüsselung + MIC) und schickt es als Semtech-UDP an den Gateway-Bridge-Port. Geprüft am 01.11.2026: **ChirpStack akzeptiert den Uplink (MIC ok), der JS-Codec liefert alle Felder, der Decoder legt die Home-Assistant-Entities an und füllt sie** (Zähler, Geschwindigkeit, Satelliten, RSSI/SNR, letzter Uplink, `device_tracker`). Die Nutzlast des Skripts ist per Test **byte-identisch** mit der der Firmware (`test_payload_golden`). Damit ist alles hinter dem Funkmodul vorab geprüft; offen bleiben nur Funk, GNSS und die echten ITS5-Daten.

```bash
python3 scripts/simulate-uplink.py /opt/chirpstack/car_device.json     # erscheint wie ein echter Uplink
```

## Dateien
| Datei | Zweck |
|---|---|
| `src/its_parse.h` | ITS5-Strom, 802.11p/GeoNetworking/BTP-Erkennung, Nutzlast (ohne Arduino-Abhängigkeit) |
| `src/main.cpp` | Hardware: UARTs, GNSS, LoRaWAN |
| `src/eu868_single.h` | Einkanal-Bandplan, übernommen aus dem IceGeiger-Projekt |
| `chirpstack-codec.js` | Payload-Decoder für ChirpStack |
| `test/` | Unity-PC-Tests, Codec-Test |

## Bekannte Grenzen
- **Signierte Pakete** (IEEE 1609.2): Der Knoten packt die übliche Form `signedData{unsecuredData}` per Minimal-OER-Durchgriff aus und zählt nach BTP-Port (CAM/DENM/…). **Signatur und Zertifikat werden nicht geprüft.** Passt das Layout nicht, zählt das Paket als `secured`. Die Testvektoren stammen aus dem ASN.1-Schema des Decoders; echte Funkdaten stehen noch aus. Die vollständige Dekodierung macht der Heimserver.
- Keine Kreuzungs-ID/Ampelzustände im Funk-Uplink (ASN.1-Dekodierung auf dem ESP32 ist offen).
- Frame-Zähler (ABP) wird nicht gespeichert; das Gerät in ChirpStack hat daher die Frame-Counter-Prüfung aus.
- Duty-Cycle: ein Uplink pro Minute bei SF9 liegt klar unter 1 %.
