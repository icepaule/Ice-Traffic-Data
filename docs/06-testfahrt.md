# 6 – Testfahrt

1. **Schreibtisch:** Bridge → lokaler Broker (`mqtt://<server>:1885`), Dashboard öffnen, Zähler `frames` beobachten.
2. **Erster Test an bekannter RSU** im TEMPUS-Testfeld (Münchner Norden), z. B. Lerchenauer Straße / Spiridon-Louis-Ring. Ob dort aktuell gesendet wird, ist vor Ort zu bestätigen.
3. Danach **Ottobrunn** – dort ist bisher *keine* ITS-G5-Ampel belegt („unbestätigt", nicht „nicht vorhanden"). Auch CAM von Serienfahrzeugen und Autobahn-Baustellenwarner beobachten.

## Zu protokollieren (Dashboard)
Pakete/min, Zähler je Typ (`CAM`, `DENM`, `SPATEM`, `MAPEM`), `secured`, `undecoded`, `decode_error_*`, sichtbare Stationen, DENM mit Gültigkeit, Lücken (MQTT-Abbrüche).

## Wenn `undecoded` hoch ist
Rohhexdump (`pio device monitor` am C5) mit `text2pcap` → Wireshark prüfen und die Ergebnisse mit dem Parser (`decoder/its_decoder/gn.py`) vergleichen – siehe Risiken in [09](09-decoder.md).
