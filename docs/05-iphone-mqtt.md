# 5 – iPhone-Hotspot & MQTT

## Hotspot
*Einstellungen → Persönlicher Hotspot*: Zugriff erlauben und **„Kompatibilität maximieren"** aktivieren (2,4 GHz, WPA2 – der ESP32-C3 kann kein 5 GHz). SSID/Passwort in der Web-Konfiguration der Brücke eintragen. Die Brücke hat eine Konfigurationsseite für MQTT (Protokoll, Host, Port, User, Passwort).

## MQTT zu OpenTrafficMap
| Parameter | Wert (laut Projektseite, vor Nutzung prüfen) |
|---|---|
| Server | `mqtts://cits1.opentrafficmap.org:8883` |
| Auth | kein Benutzer/Passwort |
| Topics | `its/<node>/status` (retained), `its/<node>/info` (JSON), `its/<node>/packet` (roh) |

Ablauf: Brücke → iPhone-Hotspot → Internet → OpenTrafficMap → Safari (<https://opentrafficmap.org>).

## Datenschutz
- Mobiler Empfänger: **keinen festen Standort** (z. B. Zuhause) als Empfängerposition veröffentlichen.
- Eingeliefert werden Rohpakete inkl. CAM fremder Fahrzeuge (pseudonymisiert).
- Wer das nicht möchte: eigenen Broker verwenden (siehe [Ausbau](07-offene-punkte.md)).
