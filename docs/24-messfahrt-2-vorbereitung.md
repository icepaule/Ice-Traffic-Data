# 24 – Messfahrt 2: Vorbereitung und Checkliste

Stand 09.11.2026. Ziel: dieselbe Strecke wie Fahrt 1 mit vollständigem Mitschnitt (alle Pakete, Feldstärke, Zähler). Planungsgrundlage: [22](22-plan-verbesserungen.md), Ergebnisse der ersten Fahrt: [20](20-auswertung-testfahrt-1.md).

## Gerätestand vor der Fahrt (geprüft)

| Gerät | Firmware | Stand |
|---|---|---|
| Traffik-Sniffer (C5) | Patch 0001–0003 (ITS6, 921 600 Baud, Zähler) | `stats` zeigt `baud=921600` |
| GPS-LoRa (XIAO) | Nutzlast v2, Schreibpuffer 1 MB im PSRAM | Mitschnitt geleert (`frb` 0), GNSS-Fix, LoRa sendet |
| Trafik-CPU (C3) | Patch 0001–0005 | MQTT-Einstellung ist **auf das Heimnetz** gesetzt, siehe unten |
| Server | Decoder mit `sniffer`-Zählern, ChirpStack-Codec v2 | läuft |

## Vor dem Losfahren

1. Alle Geräte mit Strom, Draht C5 → XIAO (und C5 → C3, falls die C3 mitfährt) prüfen.
2. XIAO-WLAN `IceCar` öffnen: `fix=1`, Satelliten ≥ 6, `frb=0`, `lost=0`, `ovf=0`. Falls Testdaten drin sind: `POST /clear` (`curl -X POST http://192.168.4.1/clear`).
3. Sniffer prüfen: auf der Statusseite steigt `its6` (ITS6-Rahmen) und die Feldstärke zeigt einen Wert, sobald ein Paket empfangen wurde.
4. Antenne senkrecht an der Scheibe, nicht neben Metall; GNSS mit freier Sicht nach oben.
5. Geräte erst nach dem Start der Fahrt bewegen, nicht während des Schreibens ins Flash ausstecken (Schreibpausen nach 3 s Funkstille).

## Während der Fahrt

- Der Mitschnitt liegt im Flash des XIAO (rund 5,6 MB frei, ein Paket belegt 394 Byte im ITS6-Format, das sind rund 14 000 Pakete). Auf der ersten Fahrt kam im Schnitt alle 7 s ein Paket an.
- LoRa-Uplinks erreichen nur das Heim-Gateway. Unterwegs ist das nur in der Nähe zu erwarten; verloren geht dadurch nichts, der Mitschnitt läuft im Flash weiter.
- Die C3 meldet nur, wenn sie ein WLAN hat (zum Beispiel ein Hotspot) und die MQTT-Einstellung auf `mqtts://its.mpauli.de:18883` mit Benutzer `car` steht. Beides muss vor der Fahrt gesetzt werden (`wifi <ssid> <pw>` in der C3-Shell, MQTT in der Weboberfläche `/config`). Fährt die C3 nicht mit, entfällt nur die Live-Anzeige.

## Nach der Fahrt

1. Vor dem Auslesen nichts löschen. Im XIAO-WLAN `frames.bin` und `log.csv` holen (`/frames.bin`, `/log.csv`), `/api` als Sicherung speichern.
2. Rohdaten nur privat ablegen. Die Daten enthalten Start und Ziel.
3. Auswertung: `python scripts/auswertung_fahrt.py DATEN AUSGABE --pcap` (Sperrzone um Start und Ziel), danach `scripts/ergebnisse_testfahrt.py` für die bereinigte Veröffentlichung. Vor jedem Push prüfen, dass keine Heimadresse und keine unbereinigten Koordinaten im Ergebnisordner stehen.
4. Kennzahlen prüfen: Spalten `rx_err`, `unicast`, `dropped`, `bad` im Log und `lost` auf der Statusseite. Stehen dort Werte, ist Material verloren gegangen oder fehlerhaft empfangen worden, und die Ursache muss geklärt werden, bevor die Zahlen als vollständig gelten.
5. Danach das Gerät leeren.

## Bekannte Einschränkungen

- Beginnt ein Paketstrom, während gerade ins Flash geschrieben wird, können Pakete verloren gehen; die Ursache ist nicht abschließend geklärt ([22](22-plan-verbesserungen.md)). Der Verlustzähler am Sniffer erfasst das nicht, `lost` am XIAO nur teilweise.
- Der Zähler `uerr` am XIAO war in einer Testreihe ungleich 0, ohne dass die Art des Fehlers geklärt ist.
- Zählerwerte `rx_err`, `unicast`, `dropped` ungleich 0 wurden bisher nie gesehen (am Schreibtisch kein Funkverkehr). Ob die Zählung bei echtem Verkehr stimmt, zeigt erst diese Fahrt.
