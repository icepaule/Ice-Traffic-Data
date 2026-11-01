# 1 – Grundlagen

Wichtig ist die Trennung von **Funkweg**, **Nachrichtenformat** und **Datenquelle**. CAM ist z. B. ein Format, ITS-G5 der Funkweg.

## Nachrichtentypen

| Nachricht | Inhalt | Nutzen |
|---|---|---|
| CAM | Position, Geschwindigkeit, Richtung, Stationstyp | Fahrzeuge auf der Karte, Empfangsdichte |
| DENM | Ereignisse (Baustelle, liegengebliebenes Fahrzeug) | Gefahrenkarte |
| SPATEM | Ampelzustand je Signalgruppe | Ampelphasen |
| MAPEM | Kreuzungsgeometrie, Fahrstreifen | Zuordnung Signalgruppe ↔ Spur |

SPATEM ohne MAPEM ist schwer nutzbar – beide werden gebraucht.

## Verkehrsdaten-Techniken in Deutschland / München

| Technik | Liefert | Mit diesem Aufbau? |
|---|---|---|
| ITS-G5 / 802.11p | Direktfunk Fahrzeug/Infrastruktur (Serienfahrzeuge, Autobahn-Baustellenwarner, TEMPUS-Testfeld München) | **Ja** |
| C-V2X (PC5) | Direktfunk auf LTE-Basis, in TEMPUS erprobt | Nein |
| LTE/5G-Backends | Stau, Reisezeit (Navi-Apps, Floating-Car-Data) | Nur über iPhone/APIs |
| UKW RDS/TMC | Kompakte Staumeldungen | Nein (anderer Empfänger) |
| DAB/TPEG | Digitale Verkehrsmeldungen | Nein |
| R09-Anmeldefunk | ÖPNV-Priorisierung an Ampeln | Nein, keine Phasenquelle |
| Mobilithek / BayernInfo (DATEX II) | Aufbereitete Verkehrs-/Baustellendaten per API | Später serverseitig kombinierbar |

## Realistische Erwartungen

- Eine bekannte Ampel-Position heißt nicht, dass sie **jetzt** SPATEM sendet.
- CAM vorbeifahrender Autos ist **kein Beleg** für Ampelabdeckung.
- In den Niederlanden laufen SPAT/MAP laut Projektautor nicht über ITS-G5 sondern über UDAP (Zugangsdaten nötig); für Deutschland ist das **zu prüfen**.
- Fahrzeug-Pseudonyme wechseln → Anzahl sichtbarer Stationen ≠ Verkehrszählung.
- Dekodierbar heißt nicht authentisch (Nachrichten können signiert sein).
