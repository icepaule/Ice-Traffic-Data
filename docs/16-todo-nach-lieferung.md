# 16 – ToDo nach Liefereingang

Reihenfolge von oben nach unten; Details zu den Schritten in [14](14-inbetriebnahme.md). Erledigtes bitte abhaken.

## A) Auspacken und prüfen
- [ ] Lieferung gegen die Stückliste prüfen ([12](12-bestellung.md)): je 2× C5, C3, XIAO-LoRa-Kit, Linx-Antenne, Grove-GPS
- [ ] Liegen dem LoRa-Kit **Antennen** bei? Liegt dem GPS ein **Grove-Kabel** bei?
- [ ] Kleinteile besorgen: Jumper, 2 USB-Datenkabel (USB-C, Micro-USB), KFZ-Netzteil 5 V ≥ 2 A
- [ ] **Pins prüfen:** C5 TX = GPIO11 (Schaltplan/Multimeter), C3 GPIO4, XIAO GPIO44 (RX), GPIO6/5 (GPS) – bei Abweichung Doku und Firmware anpassen

## B) ITS-G5-Empfänger (C5 + C3) am Schreibtisch
- [ ] `cd firmware && ./build.sh` (Toolchain ist auf dem Server schon im Cache)
- [ ] **C5 flashen** (`./build.sh flash-c5 /dev/ttyACM0`), 5-V-Brücke abgezogen
- [ ] C5 allein: LED blinkt jede Sekunde; `pio device monitor` zeigt Hexdumps (nur wenn gesendet wird)
- [ ] **C3 flashen** (`./build.sh flash-c3 /dev/ttyUSB0`)
- [ ] C3: `wifi <ssid> <passwort>`, Weboberfläche öffnen, MQTT auf `mqtt://<NUC-IP>:1885` stellen (zu Hause, ohne TLS)
- [ ] C5 → C3 verdrahten (GND, 5 V, TX → GPIO4); im Dashboard erscheinen `frames` (falls Funk vorhanden)
- [ ] Antennenposition testen (Fensterbank vs. Armaturenbrett)

## C) Erste echte Daten – wichtigster Test für den Decoder
- [ ] Hexdump mitschneiden → `text2pcap -l 105 message.txt message.pcap` → in Wireshark ansehen
- [ ] Dashboard: Zähler `undecoded`, `secured`, `decode_error_*` beobachten
- [ ] **Annahmen prüfen:** sind die Pakete signiert? Common Header innerhalb der 1609.2-Hülle? SPATEM/MAPEM-Version?
- [ ] Bei Abweichungen `decoder/its_decoder/gn.py` anpassen, Mitschnitt als Testfall ablegen (ohne personenbezogene Daten)

## D) Im Auto
- [ ] KFZ-Netzteil, Gehäuse/Befestigung, Antenne frei
- [ ] iPhone-Hotspot: „Kompatibilität maximieren" an; Bridge-WLAN auf Hotspot umstellen
- [ ] Bridge-MQTT auf `mqtts://its.mpauli.de:18883`, Benutzer `car`, Passwort aus `/opt/ice-traffic-data/secrets/car.pass`
- [ ] Kontrolle von außen: im Dashboard (https://its.mpauli.de) erscheint der Empfänger als online
- [ ] **Testfahrt** TEMPUS-Nord (Lerchenauer Str./Spiridon-Louis-Ring), danach Ottobrunn; Zähler und Orte notieren

## E) LoRa-Auto-Knoten
- [ ] `secrets.h` vorhanden (`scripts/provision-chirpstack.py` hat sie erzeugt, liegt nur lokal) – sonst Skript erneut ausführen
- [ ] Antenne **vor** dem ersten Senden anstecken
- [ ] `cd firmware/lora-car-node && pio run -t upload`; Seriell-Log: `radio.begin state=0`, `activateABP`, Uplinks
- [ ] In ChirpStack: Gerät `ice-car` zeigt Uplinks; Gateway online (ein simulierter Test-Uplink mit hohem Frame-Zähler ist bereits verzeichnet, `skipFcntCheck` ist aktiv)
- [ ] In Home Assistant: Auto-Knoten-Entities werden gefüllt (RSSI/SNR, Zähler, Tracker)
- [ ] **Reichweitentest:** Strecken abfahren, Abbruchentfernung zum Heim-Gateway notieren
- [ ] Falls nötig: Gateway-Antenne/-Standort verbessern oder 8-Kanal-Gateway erwägen

- [ ] Schlägt der erste echte Uplink fehl, zuerst `scripts/simulate-uplink.py` laufen lassen: kommt der durch, liegt der Fehler im Funk/Knoten, nicht in ChirpStack/HA

## F) Auswerten und dokumentieren
- [ ] Messprotokoll anlegen (Pakete/min, Typen, signiert/unsigniert, Orte)
- [ ] Echte Screenshots ergänzen (Demo-Bilder ersetzen; Orte/Kennungen unkenntlich machen)
- [ ] README/Doku-Status von „Entwurf" auf „getestet" setzen, Annahmen aus [09](09-decoder.md) bestätigen oder korrigieren
- [ ] Optional: Antenne A/B-Vergleich ([11](11-antennen.md))

## G) TEMPUS
- [ ] Nach den ersten belastbaren Messungen die Mail aus [15](15-tempus.md) mit Name/Kontakt versenden
- [ ] Antwort auswerten, ggf. Messformat abstimmen

## H) Wartung und Sicherheit
- [ ] DE-IP-Liste auf der pfSense monatlich erneuern ([13](13-dashboard-veroeffentlichen.md))
- [ ] Prüfen, dass das erneuerte Let's-Encrypt-Zertifikat im Broker und im HAProxy ankommt (Erneuerung ca. Ende Dezember 2026)
- [ ] MQTT-Passwort (`car`) nach dem ersten Feldeinsatz rotieren
- [ ] MQTT-Port 18883 optional auf deutsche Quell-IPs beschränken
- [ ] Dashboard-Login mit Authentik (2FA) einmal im Browser prüfen
- [ ] Signierte Pakete: Der Knoten packt `signedData{unsecuredData}` aus und zählt nach Typ (ohne Signaturprüfung). Prüfen, ob in den echten Daten `secured` (= Layout nicht erkannt) klein bleibt; sonst Mitschnitt gegen `its_parse.h` auswerten

# Zugänge zum Ansehen (ohne Hardware)

| Was | Adresse | Anmeldung |
|---|---|---|
| ITS-Dashboard (LAN) | `http://10.10.0.100:8097` | keine |
| ITS-Dashboard (Heimnetz) | `https://its.mpauli.de` oder `http://10.10.0.100:8097` | keine, direkt |
| ITS-Dashboard (Internet) | `https://its.mpauli.de` | Authentik-Login (SSO + 2FA), nur Benutzer `mpauli` |
| Home Assistant (LAN) | `http://10.10.0.100:8123` → Einstellungen → Geräte → „Ice-Traffic-Data" | wie gewohnt |
| ChirpStack | `http://10.10.0.100:8180` → Applications → IceTraffic → ice-car | Benutzer `admin`, Passwort lokal in `/opt/chirpstack/geiger_device.json` |
| Broker (LAN, anonym) | `10.10.0.100:1885` | – |
| Dokumentation | https://icepaule.github.io/Ice-Traffic-Data/ | öffentlich |
| Repository | https://github.com/icepaule/Ice-Traffic-Data | öffentlich |

Home-Assistant-Entities (Gerät „Ice-Traffic-Data"): `sensor.ice_traffic_data_pakete_pro_minute`, `…_sichtbare_fahrzeuge_cam`, `…_aktive_gefahrenmeldungen_denm`, `…_kreuzungen_mit_ampeldaten_spatem`, `…_bekannte_kreuzungen_mapem`, `…_letzte_gefahrenmeldung`, `binary_sensor.ice_traffic_data_empfaenger_online`; Auto-Knoten: `sensor.ice_traffic_data_auto_knoten_*` und `device_tracker.ice_traffic_data_auto_knoten_auto` (bis zum ersten Uplink „nicht verfügbar").
