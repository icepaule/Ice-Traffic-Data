# 23 · TEMPUS beendet? Nachfolge, heutige Einsätze und Erweiterungen des Setups

> **Stand 08.11.2026.** Jede Aussage hat eine Quelle in eckigen Klammern (Verzeichnis unten) oder ist als **eigene Messung/Rechnung** gekennzeichnet. Was ich nicht belegen konnte, steht als „nicht verifiziert“ da. Ergänzt [15 · TEMPUS](15-tempus.md) und [21](21-testfahrt-1-timeline-karte-verbesserungen.md).

## 1 · Ist TEMPUS beendet?

**Ja, das Projekt ist beendet.**
- „TEMPUS lief bis Ende Dezember 2023. Die Ergebnisse wurden auf der IAA 2023 präsentiert.“ [1] Die TUM führt es als „completed: 2023“ [2].
- Die Projektseite sagte vor dem Ende, die rund 40 städtischen Projekt-RSU stünden „auch nach Projektabschluss interessierten Unternehmen als offene Plattform für Erprobungen zur Verfügung“ [3]. **Ob und wie diese RSU heute betrieben werden, nennt keine der Quellen.** Die Seite der Stadt zur Nachnutzung habe ich nicht gefunden.
- Die interaktive TEMPUS-Karte ist weiter online [4]. Sie zeigt **67 Ampeln mit RSU** (45 im Stadtgebiet, 22 im Umland): **17 nur ITS-G5, 14 hybrid (ITS-G5 und C-V2X), 36 nur C-V2X** (eigene Auszählung der KML-Datei der Karte [4]). Das Leitfaden-PDF nennt „rund 65 Ampeln“ [5], die Projektseite „rund 40“ [3]; die Angaben stimmen nicht überein.
- **Konsequenz für uns:** Nur **31 von 67** dieser Ampeln (17 + 14) funken laut Karte überhaupt ITS-G5. Die 36 C-V2X-Ampeln kann der Traffik-Sniffer **nicht** hören (anderer Funkstandard, siehe Abschnitt 4).

### Folgeprojekte und heutiger Einsatz ähnlicher Technik

| Projekt / Einsatz | Fakt | Quelle |
|---|---|---|
| **MINGA** (München) | Nachfolgeprojekt von TEMPUS, Ziel: ÖPNV automatisieren (On-Demand-Fahrzeuge und Busse); Laufzeit **bis Mitte 2027** | [1] |
| MINGA, Stand Oktober 2026 | Seit September 2026 fährt ein automatisierter MAN-Bus auf der **Linie 178** zwischen Petuelring und Freimanner Hölzl (mit Testfahrern); Konsortialführung Mobilitätsreferat der Stadt | [6] |
| **C-Roads Germany Phase 3** | Laufzeit **01.01.2025 – 31.03.2028**, Volumen 48,3 Mio. €, 50 % EU-gefördert; Partner u. a. Kassel, BASt, Autobahn GmbH, Hamburg, Frankfurt, Kaiserslautern, Dresden, Hannover. **München steht in der dort gezeigten Partnerliste nicht.** | [7] |
| **C-Roads Europa** | „6,000+ Roadside Units“, 30 % des TEN-T-Straßennetzes, „3,500+ Public transport vehicles“ (Stand 19.02.2026) | [8] |
| **Autobahn GmbH, Baustellenwarner** | Seit 2021 Regelbetrieb; bis Mai 2025 **1 000** ITS-Roadside-Stationen auf mobilen Absperrtafeln in Betrieb, ITS-G5 nach C-Roads-Profil; Kapsch-Systeme auf 8 600 von 13 000 km Autobahn | [9] |
| **Volkswagen Car2X** | Am 27.10.2025: „Mehr als zwei Millionen Fahrzeuge mit Car2X produziert“; Direktkommunikation per WLANp (= ITS-G5); Warnungen vor Staus, Unfällen, Baustellen, Einsatzfahrzeugen | [10] |
| **Digitales Testfeld Autobahn A9** | seit 2015, „etwa 140 Kilometer“ A9 zwischen Nürnberg und München; Schwerpunkte u. a. Lkw-Parkleitsystem; **ITS-G5-Sender dort nicht belegt** | [11] |
| **Böblingen** | 20 Ampeln mit V2X (Ampelphasen- und Abbiegeassistent), Pressemeldung Mai 2025 (nur als Suchtreffer gesehen, Seite nicht lesbar: **nicht verifiziert**) | [12] |
| **Testfahrt-Woche** | „C-Roads Germany X-Test November 2026“: 9.–13.11.2026 „real-world testing of C-ITS across Germany“ | [8] |

## 2 · Was wir gemessen haben, passt zu den Karten (eigene Auswertung)

Ich habe die empfangenen Fenster der ersten Testfahrt ([20](20-auswertung-testfahrt-1.md), [21](21-testfahrt-1-timeline-karte-verbesserungen.md)) mit den Ampelstandorten der TEMPUS-Karte verglichen (nur Positionen außerhalb der Sperrzone):

| Eigene Messung | Wert |
|---|---|
| „Sonstige“ Pakete im Log (alte Zählung) | 277 |
| davon in Fenstern **bis 300 m** neben einer Ampel mit ITS-G5- oder Hybrid-RSU | **249 (90 %)** |
| Ort dieser 249 | 52 Pakete 66 m von der Hybrid-Ampel an der **B 2 R / Petuelring**, dann 104, 93 und 24 Pakete beim Entfernen entlang der **Schleißheimer Straße** (152, 229 und 373 m) |
| Fenster mit GPS-Fix bis 300 m neben einer solchen Ampel | 23 (davon nur **3 mit Empfang**); zum Vergleich weiter entfernt: 129 von 654 Fenstern mit Empfang |

**Deutung (nicht belegt):** Die alte Firmware zählte unsignierte Pakete als „sonstige“ ([20](20-auswertung-testfahrt-1.md#der-fehler-und-seine-behebung)). Dass 249 von 277 an einer Stelle neben einer Ampel mit ITS-G5-Hybrid-RSU auftraten, **spricht dafür, dass es Sendungen dieser RSU waren** (z. B. SPATEM und MAPEM). **Gegenargument:** An den übrigen 20 Fenstern neben ITS-G5-Ampeln kam fast nichts an (nur 3 von 23 Fenstern mit Empfang). Entweder senden die meisten dieser RSU heute nicht, oder wir standen außer Reichweite oder ohne Sichtverbindung. Wir haben die Pakete nicht gespeichert, daher fehlt der Beweis. Das ist der wichtigste Grund für die nächste Fahrt: **dieselbe Stelle noch einmal, diesmal mit V1 (alle Pakete speichern).** Auf der Dashboard-Karte sind die Ampeln als rote und orange Punkte mit Google-Maps-Link eingezeichnet.

## 3 · Dashboard: Orte (POI) und Baustellen

https://its.mpauli.de/ zeigt jetzt auch ohne Funkdaten:
- **67 Ampeln mit RSU** aus der TEMPUS-Karte, farbig nach Funktechnik (ITS-G5, hybrid, C-V2X), mit nächster Straße und **Links zu Google Maps, Route und Street View**. Die Links folgen dem dokumentierten URL-Schema der Google-Maps-URLs [13].
- **20 Use Cases** der Karte, das Testfeld (Straßennetz Stadt und Land), die Buslinien 178 und 180 und die A9 als Digitales Testfeld Autobahn.
- Eine **Liste** der 31 Ampeln mit ITS-G5-Funk (Ziele für Messfahrten).
- **Baustellen, Sperrungen und Warnungen der Autobahn GmbH** im Umkreis von 70 km um München, live. Stand der ersten Abfrage: **120 Einträge** (A99: 34 Baustellen, 11 Sperrungen; A8: 29; A94: 13; A9: 11; A96: 9; A92: 7). Sie zeigen, wo ein **Baustellenwarner** (mobile Absperrtafel mit ITS-G5-Sender [9]) stehen kann.

Die POI-Datei erzeugt `scripts/poi_tempus.py` aus der KML-Datei der TEMPUS-Karte (öffentliche Karte [4]) und OpenStreetMap-Straßennamen (Nominatim, 1 Anfrage/s [14]). Die Autobahn-Daten ruft der Decoder alle 10 min serverseitig ab (`decoder/its_decoder/autobahn.py`). Die Nutzungsbedingungen dieser Daten habe ich **nicht geprüft**; sie liegen nicht im Repo.

## 4 · Weitere Informationen aus dem Verkehr: was ist nutzbar, was fehlt?

| Quelle | Was sie liefert | Mit dem jetzigen Setup? | Was zu tun ist | Beleg |
|---|---|---|---|---|
| ITS-G5 **CAM** | Position, Tempo, Maße, Lichter, Pfad der Fahrzeuge | **ja**, empfangen | – | [20](20-auswertung-testfahrt-1.md) |
| ITS-G5 **DENM** | Gefahrenmeldungen (Stau, stehendes Fahrzeug, Baustelle) | **ja**, empfangen | – | [20](20-auswertung-testfahrt-1.md) |
| ITS-G5 **SPATEM/MAPEM** | Ampelphasen und Kreuzungsgeometrie | **nicht belegt** (siehe Abschnitt 2) | V1 und Messfahrt an Ampeln mit ITS-G5-RSU | [4], [15] |
| ITS-G5 **Baustellenwarner** | DENM der Absperrtafeln der Autobahn GmbH | **ja, zu erwarten** (gleiche DENM) | Fahrt zu einer Tagesbaustelle; Orte liefert der Autobahn-Layer | [9] |
| ITS-G5 **IVIM, CPM, SREM, SSEM, SAEM** | Verkehrszeichen-Infos, Wahrnehmung von Objekten, Anforderung von Ampelbevorzugung | **nicht ausgewertet**: BTP-Ports 2005–2009 sind definiert, die Firmware kennt nur 2001–2004 | V5 (Beifang nach Port aufschlüsseln), dann Schemas für die Dekodierung ergänzen | [15] |
| **C-V2X (PC5)** | Direktkommunikation per Mobilfunk-Sidelink, **36 der 67 TEMPUS-Ampeln** nur so | **nein**: anderer Funkstandard, nicht 802.11p | eigener Empfänger nötig (Modem oder SDR). Offene Forschungswerkzeuge gibt es, ob eines C-V2X im Straßenverkehr passiv dekodiert, habe ich **nicht geprüft** [16] | [4] |
| **Autobahn-API** (Baustellen, Sperrungen, Warnungen, Webcams, Lkw-Parkplätze, Ladesäulen) | Offene REST-API ohne Schlüssel; Antworten live geprüft (A9 Baustelle München-Nord) | **jetzt im Dashboard** (Baustellen, Sperrungen, Warnungen) | Webcams, Parkplätze, Ladesäulen könnten ergänzt werden | [17] |
| **Mobilithek** (Nationaler Zugangspunkt, DATEX II) | Baustellen- und Verkehrsdaten aus ganz Deutschland | **nein** | Konto und Datenangebot wählen, DATEX-II-Abruf bauen; Details zu Registrierung und Lizenz habe ich nicht gefunden | [9], [18] |
| **ADS-B** (Flugzeuge) | Flugverkehr | im Bestand (IceFlightRadar), kein Straßenverkehr | – | – |

### Wie das Setup erweitert würde (nach Aufwand)
1. **V1 und V5 (Firmware):** alle Pakete speichern und jeden Port zählen. Damit lassen sich SPATEM/MAPEM, IVIM, CPM nachweisen oder ausschließen. Plan: [22](22-plan-verbesserungen.md).
2. **Fahrtplanung mit Daten statt Zufall:** Autobahn-Layer (Tagesbaustelle in der Nähe?) und ITS-G5-Ampelliste aus dem Dashboard.
3. **Autobahn-API im Decoder:** Baustellen als Zeitreihe mitschreiben und später mit empfangenen Baustellen-DENM abgleichen (Hat der Warner gesendet, wo die API eine Baustelle meldet?).
4. **Mobilithek-Abruf:** erst nach Klärung von Konto und Lizenz.
5. **C-V2X-Empfang:** eigenes Projekt mit anderer Hardware; erst nach Kauf-/Verfügbarkeitsprüfung.

### Rechtliches und Datenschutz (Hinweis, keine Rechtsberatung)
- Wir **senden nichts**; der Sniffer hört den Rundfunk mit. Die Bundesnetzagentur führt eine Allgemeinzuteilung für ITS im 5,9-GHz-Band; **Einzelheiten und Befristung habe ich nicht verifiziert** [19].
- CAM und DENM tragen **Pseudonyme** (Kennungen wechseln wöchentlich, [20](20-auswertung-testfahrt-1.md#1-zertifikate-authorization-tickets)). Wer Rohdaten Dritter veröffentlicht, sollte das bewusst entscheiden (siehe [21](21-testfahrt-1-timeline-karte-verbesserungen.md#1-datenschutz-und-was-im-repo-liegt)).
- Weitere Funkquellen von Verkehrsteilnehmern (z. B. Reifendrucksensoren, Bluetooth/WLAN der Geräte) sind **nicht Teil des Projekts**; sie lassen sich Personen oder Fahrzeugen zuordnen und werfen eigene Datenschutzfragen auf. Dazu habe ich nichts recherchiert.

## Quellenverzeichnis

Abgerufen am 08.11.2026. „selbst gelesen“ = Inhalt der Seite oder Datei geprüft.

1. SWM, „Automatisierung von Bussen: Förderprojekt TEMPUS“ (20.12.2023), MINGA bis Mitte 2027: <https://www.swm.de/unternehmen/magazin/innovation/automatisierung-bus> (selbst gelesen).
2. TUM, TEMPUS „completed: 2023“: <https://www.mos.ed.tum.de/en/vt/forschung/projekte/abgeschlossene-projekte/tempus-completed-2023/> (selbst gelesen).
3. TEMPUS, Aufbau Testfeld („rund 40 Ampeln“, „offene Plattform“): <https://tempus-muenchen.de/aufbautestfeld> (selbst gelesen).
4. TEMPUS, interaktive Karte (Google My Maps, eingebettet): <https://tempus-muenchen.de/karte>; Datei: `https://www.google.com/maps/d/kml?mid=1oOJLO9c4-xhMJ-eVpLNPi818OhqZALXl&forcekml=1` (selbst ausgewertet: Ordner „LSAs mit RSUs“, „Use Cases“, „Testfeld“).
5. TEMPUS, Leitfaden für Kommunen („rund 65 Ampeln“): <https://muenchenunterwegs.de/index.php/content/2455/download/tempus-leitfaden-fuer-kommunen-web.pdf> (selbst gelesen).
6. SWM/MVG, Pressemitteilung Oktober 2026 zu MINGA (Linie 178): <https://www.swm.de/unternehmen/presse/pressemitteilungen/2026/10-2026/mvg-minga-start-testbetrieb> (selbst gelesen); Projektseite: <https://www.swm.de/unternehmen/magazin/innovation/projekt-minga>.
7. Stadt Kassel, „C-Roads Germany – Phase 3“: <https://www.kassel.de/buerger/verkehr_und_mobilitaet/verkehrsprojekte/c-roads-germany-phase-3.php> (selbst gelesen).
8. C-Roads Platform (Stand 2026-02-19): <https://www.c-roads.eu/platform.html> (selbst gelesen).
9. Kapsch TrafficCom, Pressemitteilung 20.05.2025 (1 000 IRS, 8 600 km, Mobilithek): <https://kapsch.net/en/press/releases/ktc-20250520-pr-en> (selbst gelesen).
10. Volkswagen Newsroom, 27.10.2025, „Mehr als zwei Millionen Fahrzeuge mit Car2X produziert“: <https://www.volkswagen-newsroom.com/de/pressemitteilungen/meilenstein-fuer-mehr-verkehrssicherheit-mehr-als-zwei-millionen-fahrzeuge-mit-car2x-produziert-19909> (selbst gelesen, Details WLANp über Suchtreffer).
11. BASt, Digitales Testfeld Autobahn: <https://www.bast.de/DE/Themen/Fahren/HF_3/Massnahmen/digitales-testfeld.html> (selbst gelesen).
12. Yunex Traffic, V2X in Böblingen: <https://www.yunextraffic.com/de/newsroom/v2x-boeblingen/> (Seite war nicht abrufbar, nur Suchtreffer; **nicht verifiziert**).
13. Google Maps URLs: <https://developers.google.com/maps/documentation/urls/get-started> (selbst geprüft: `search`, `dir`, `pano`).
14. OSMF Nominatim Usage Policy: <https://operations.osmfoundation.org/policies/nominatim/> (selbst gelesen).
15. ETSI TS 103 248 V2.2.1, BTP-Portnummern: <https://www.etsi.org/deliver/etsi_ts/103200_103299/103248/02.02.01_60/ts_103248v020201p.pdf> (selbst gelesen, Tabelle 1).
16. C-V2X-Sidelink-Werkzeuge (nur Suchtreffer, **nicht geprüft**): <https://github.com/feron-tech/lte-sidelink>, <https://arxiv.org/pdf/2103.13212.pdf>, <https://publica.fraunhofer.de/handle/publica/412345>.
17. Autobahn-App-API, Beschreibung: <https://github.com/bundesAPI/autobahn-api> (selbst gelesen); Daten: <https://verkehr.autobahn.de/o/autobahn/> (selbst abgerufen, 08.11.2026).
18. Mobilithek: <https://mobilithek.info> (nur Suchtreffer zu Datenangeboten, **nicht geprüft**).
19. Bundesnetzagentur, Allgemeinzuteilungen: <https://www.bundesnetzagentur.de/allgemeinzuteilungen> (nur Verzeichnis, **Inhalt nicht geprüft**).
