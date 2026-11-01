# 4 – Firmware bauen & flashen

Beide Teile **aus demselben Repo-Stand** verwenden (serielles ITS5-Format ist projektspezifisch).

```bash
git clone https://github.com/bertrik/its-g5-receiver.git
cd its-g5-receiver
pip install platformio

# 1) Sniffer (ESP32-C5) – nur C5 per USB angeschlossen
cd esp32-c5-sniffer
pio run -t upload

# 2) Bruecke (ESP32-C3) – nur C3 per USB angeschlossen
cd ../esp32-c3-bridge
pio run -t upload
```

Die genauen PlatformIO-Environments und Pinbelegung stehen in den README/`platformio.ini` des Repos – bei abweichender Boardvariante dort anpassen. *(Beim Erstellen dieser Doku nicht im Detail geprüft, siehe [Offene Punkte](07-offene-punkte.md).)*

## Schreibtischtest

1. C5 allein: `pio device monitor` – Pakete erscheinen als Hexdump.
2. Hexdump in Wireshark ansehen: `text2pcap -l 105 message.txt message.pcap && wireshark message.pcap`
3. C3 allein: Webseite zur MQTT-Konfiguration erreichbar? (WLAN-Zugang siehe Schritt 5)
4. Erst danach beide verbinden. „Keine Pakete" ≠ „Brücke defekt" – am Schreibtisch sendet ggf. niemand.
