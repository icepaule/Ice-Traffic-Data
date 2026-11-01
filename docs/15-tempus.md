# 15 – TEMPUS (Testfeld München): Recherche und Unterstützungsangebot

## Was TEMPUS ist (Stand der Recherche, 01.11.2026)
- Testfeld für automatisiertes und vernetztes Fahren in München (Stadtteil zwischen Olympiapark und Kieferngarten sowie Umland zwischen A9, A99 und Unterschleißheim). Projektlaufzeit offiziell 01.01.2021 – 30.06.2023, **13 Partner** (u. a. Landeshauptstadt München als Projektleitung, BMW, TUM, Yunex, SWM, Bayerische Straßenbauverwaltung).
- **Zwei Funktechniken parallel:** WLAN-basiertes **ITS-G5** und mobilfunkbasiertes **C-V2X**. Straßenseitige Einheiten (RSU) senden **SPaT** (Ampelphasen) und **MAP** (Kreuzungsgeometrie).
- Rund **65 Ampeln** mit RSU ausgestattet (die Projektseiten nennen an anderer Stelle „etwa 40" – die Zahlen sind nicht abgeglichen). Genannte Standorte: Lerchenauer Str./Spiridon-Louis-Ring, Kieferngarten-/Heidemannstraße (Bus 178, Rückkanal), Allacher Str./Wintrichring (kamerabasierter Abbiegeassistent).
- **Offen für Dritte:** Das Testfeld „steht auch nach Projektabschluss interessierten Unternehmen als offene Plattform für Erprobungen zur Verfügung"; Testfahrten sind kostenfrei, aber nur nach **Registrierung** (und nur für Unternehmen, keine Mitfahrt).
- Daten: Referenzkarte im OpenDRIVE-Format; Verkehrsdaten wurden über das Backend bereitgestellt und über die **Mobilithek** veröffentlicht.
- **Kontakt (laut Projekt-/Stadtseiten):** tempus@muenchen.de; Projektleitung beim Mobilitätsreferat der Landeshauptstadt München. Ein Ansprechpartner ist öffentlich nicht genannt.

Quellen: [tempus-muenchen.de](https://tempus-muenchen.de/en), [FAQ](https://tempus-muenchen.de/en/faq), [Aufbau Testfeld](https://tempus-muenchen.de/aufbautestfeld), [muenchenunterwegs.de/angebote/tempus](https://muenchenunterwegs.de/angebote/tempus).

## Was als Privatperson sinnvoll angeboten werden kann
Die Registrierung für Testfahrten richtet sich an Unternehmen; **passives Mitlesen** des ITS-G5-Broadcasts braucht keinen Zugang (es wird nicht gesendet). Ein Angebot sollte genau das benennen:

| Angebot | Nutzen für TEMPUS/Stadt |
|---|---|
| **Empfangsmessungen aus Sicht eines Serienfahrzeugs** (Pakete/min, Anteil SPATEM/MAPEM/CAM/DENM, signiert/unsigniert) entlang der Teststrecken | unabhängige Rückmeldung, welche RSU im Alltag tatsächlich senden |
| **Reichweiten-/Abdeckungsdaten** (Orte mit Empfang, Antenne im Fahrzeug) | Planung weiterer Standorte, Prüfung der Funkabdeckung |
| **Open-Source-Decoder** (GeoNetworking, IEEE 1609.2, CAM/DENM/SPATEM/MAPEM) und Dokumentation | Werkzeug für Kommunen/Hochschulen, Interoperabilitätstests |
| **Mitschnitte** (PCAP) nach Absprache | Fehlersuche; keine personenbezogenen Daten ohne Abstimmung |
| Hinweise auf **Dekodierprobleme** (z. B. Versionen, Erweiterungen) | Qualitätssicherung der Nachrichten |

## Fragen an das Projekt
1. Welche RSU senden **aktuell** ITS-G5 (Kanal, Nachrichtentypen, SPATEM/MAPEM-Version), und welche nur C-V2X?
2. Ist **passiver Empfang und die Veröffentlichung aggregierter Messwerte** (ohne Kennzeichen-/Personenbezug) in Ordnung? Gibt es Vorgaben zum Datenschutz?
3. Gibt es eine **Spezifikation/Profil** der gesendeten Nachrichten (Zertifikatskette, PSIDs)?
4. Möchte das Projekt die Messungen **in einem bestimmten Format** (PCAP, CSV, GeoJSON)?
5. Gibt es einen Weg, **als Privatperson/Verein** (z. B. THW-Umfeld, Forschungsinteresse) an der offenen Plattform teilzunehmen?

## Entwurf der E-Mail (nicht versendet)

**An:** tempus@muenchen.de
**Betreff:** Angebot: unabhängige ITS-G5-Empfangsmessungen im TEMPUS-Testfeld (Open Source)

> Sehr geehrte Damen und Herren,
>
> ich beschäftige mich privat und aus technischem Interesse mit dem Empfang von C-ITS-Nachrichten (ITS-G5) und habe dafür einen kostengünstigen Empfänger auf Basis von ESP32-C5-Mikrocontrollern aufgebaut. Dazu entwickle ich einen quelloffenen Decoder (GeoNetworking, IEEE 1609.2, CAM/DENM/SPATEM/MAPEM), der alle Daten ausschließlich lokal verarbeitet. Die Dokumentation ist öffentlich: https://github.com/icepaule/Ice-Traffic-Data
>
> Ich habe gesehen, dass das TEMPUS-Testfeld nach Projektabschluss als offene Plattform weiter besteht, und möchte meine Messungen gern zur Verfügung stellen. Ich empfange ausschließlich passiv (es wird nicht gesendet) und würde gern:
>
> - im Testfeld (Münchner Norden) die tatsächliche Empfangbarkeit von SPaT/MAP je Kreuzung aus Sicht eines Fahrzeugs messen (Paketraten, Nachrichtentypen, signiert/unsigniert, Reichweiten),
> - die Ergebnisse als aggregierte Auswertung (ohne Personenbezug) und den Decoder als Open Source bereitstellen,
> - Auffälligkeiten beim Dekodieren (Versionen, Erweiterungen) an Sie zurückmelden.
>
> Dazu hätte ich einige Fragen: (1) Welche RSU senden aktuell ITS-G5 (Kanal, Nachrichtentypen, Version), welche nur C-V2X? (2) Ist passiver Empfang samt Veröffentlichung aggregierter Messwerte aus Ihrer Sicht unproblematisch, und gibt es Datenschutzvorgaben? (3) Gibt es eine Beschreibung des Nachrichtenprofils bzw. der Zertifikatsstruktur? (4) In welchem Format wären Messdaten für Sie nützlich? (5) Gibt es für Privatpersonen bzw. ehrenamtliche Organisationen einen Weg, an der offenen Plattform teilzunehmen?
>
> Über eine kurze Rückmeldung oder einen Ansprechpartner würde ich mich sehr freuen. Gern stelle ich das Projekt auch persönlich vor.
>
> Mit freundlichen Grüßen
> [Name]
> [E-Mail] · [Telefon, optional]

**Hinweise vor dem Senden:** Name/Kontaktdaten einsetzen; erst nach den ersten echten Messungen kann ein konkretes Ergebnis genannt werden – bis dahin ist das Schreiben ein Angebot und eine Anfrage. Keine Standortdaten Dritter oder Roh-CAMs mitsenden.
