# 5 – iPhone-Hotspot & MQTT (alles privat)

Entscheidung: **keine Einlieferung an OpenTrafficMap**. Die Bridge sendet nur an den eigenen Broker.

## Hotspot
*Einstellungen → Persönlicher Hotspot*: Zugriff erlauben und **„Kompatibilität maximieren"** (2,4 GHz, WPA2; der C3 kann kein 5 GHz). Per `wifi <ssid> <pw>` in der Bridge eintragen.

## MQTT-Konfiguration der Bridge (Weboberfläche → Configuration)
| Feld | Wert |
|---|---|
| Protokoll | `mqtts` |
| Host | `its.<deine-domain>` (siehe [Heimserver-Anbindung](08-heimserver.md)) |
| Port | z. B. `18883` |
| User/Passwort | eigener Account, nur Schreibrecht auf `its/#` |

Topics (vom Firmware-Autor): `its/<node>/status` (retained), `its/<node>/info`, `its/<node>/packet` (roh), `its/<node>/stats`.

## ⚠ VPN-Falle
Ein VPN **auf dem iPhone** schützt nur dessen eigenen Verkehr. Geräte am Persönlichen Hotspot (der ESP32) laufen nach gängiger Erfahrung **nicht** durch das VPN des iPhones. Darum: TLS-MQTT mit Zugangsdaten zum Heimserver (Schritt 8), oder VPN auf dem ESP32 selbst (aufwendig).
