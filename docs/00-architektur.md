# 0 – Architektur, Setup und Datenfluss

## Setup im Auto (Hardware)
![Diagramm 00-architektur-0](diagrams/00-architektur-0.png)

<details><summary>Mermaid-Quelltext</summary>

```mermaid
flowchart LR
    ANT_G5(["PCB-Antenne 5,9 GHz"]) --- C5
    PS["KFZ-USB-Netzteil 5 V"] --> C3
    C5["ESP32-C5-DevKitC-1<br/>ITS-G5-Sniffer"] -- "5 V + GND" --- C3["ESP32-C3-DevKitM-1<br/>WLAN/MQTT-Bruecke"]
    C5 -- "TX GPIO11 → GPIO4<br/>115200 Baud, ITS5-Format" --> C3
    C5 -. "TX parallel (nur Mithoeren)" .-> S3["XIAO ESP32S3 + Wio-SX1262<br/>LoRa-Auto-Knoten (geplant)"]
    GPS["Grove GPS Air530"] -- UART --> S3
    ANT_L(["868-MHz-Antenne U.FL"]) --- S3
    PS --> S3
    C3 -- "WLAN 2,4 GHz" --> HS(["iPhone Hotspot"])
```

</details>


## Systemübersicht (Auto → Heimnetz → Anzeige)
![Diagramm 00-architektur-1](diagrams/00-architektur-1.png)

<details><summary>Mermaid-Quelltext</summary>

```mermaid
flowchart TB
    subgraph Auto
      RF["ITS-G5-Funk<br/>CAM · DENM · SPATEM · MAPEM"] --> C5["ESP32-C5 Sniffer"]
      C5 --> C3["ESP32-C3 Bruecke"]
      C5 -.-> S3["LoRa-Knoten (geplant)"]
      C3 --> HS["iPhone-Hotspot"]
    end
    subgraph Internet
      HS -- "MQTT über TLS<br/>its.mpauli.de:18883" --> FB["FritzBox<br/>Portfreigabe (offen)"]
      LORA(("LoRa 868 MHz")):::dash
    end
    S3 -.-> LORA
    subgraph Heimnetz
      FB --> PF["pfSense<br/>NAT + Ratenbegrenzung"]
      PF --> MQ["Mosquitto :18883<br/>TLS, Passwort, ACL"]
      LORA -.-> GW["Einkanal-Gateway"] -.-> CS["ChirpStack"] -.-> MQ
      MQ --> DEC["Decoder (Docker)<br/>GeoNetworking · BTP · ASN.1"]
      DEC --> DB[("SQLite<br/>7 Tage")]
      DEC --> DASH["Dashboard :8097"]
      DEC --> HAMQ["HA-MQTT-Broker<br/>Discovery"] --> HA["Home Assistant"]
    end
    subgraph Zugriff
      DASH --> HP["pfSense HAProxy :443<br/>nur DE · Basic-Auth"] --> SAF["Safari / Browser<br/>https://its.mpauli.de"]
    end
    classDef dash stroke-dasharray: 4 3;
```

</details>

Gestrichelt = geplant bzw. noch nicht gebaut oder nicht freigeschaltet.

## Datenfluss eines Pakets
![Diagramm 00-architektur-2](diagrams/00-architektur-2.png)

<details><summary>Mermaid-Quelltext</summary>

```mermaid
sequenceDiagram
    participant V as Ampel/Fahrzeug
    participant C5 as ESP32-C5
    participant C3 as ESP32-C3
    participant B as Broker (TLS)
    participant D as Decoder
    participant W as Dashboard/HA
    V->>C5: 802.11p-Frame (5,9 GHz, Broadcast)
    C5->>C5: Fehlerfreie Broadcast-Frames in Ringpuffer
    C5->>C3: "ITS5"-Header + Frame (UART)
    C3->>B: its/NODE/packet (roh, ohne ITS5-Header)
    B->>D: its/NODE/packet
    D->>D: LLC → GeoNetworking → (IEEE 1609.2) → BTP-Port
    D->>D: ASN.1-UPER-Decodierung je Nachrichtentyp
    D->>W: Zustand, Karte, Ampelphasen, HA-Entities
```

</details>


## Dekodier-Pipeline (Detail)
![Diagramm 00-architektur-3](diagrams/00-architektur-3.png)

<details><summary>Mermaid-Quelltext</summary>

```mermaid
flowchart LR
    F["Frame"] --> L["LLC/SNAP<br/>Ethertype 0x8947"]
    L --> G["GeoNetworking<br/>Basic · Common · Extended Header"]
    G --> S{"Basic Header NH"}
    S -- "1 unsigniert" --> BTP
    S -- "2 signiert" --> E["IEEE 1609.2<br/>Nutzlast entpacken"] --> BTP
    BTP["BTP-B Zielport"] --> T{"Port"}
    T -- 2001 --> CAM
    T -- 2002 --> DENM
    T -- 2003 --> MAPEM
    T -- 2004 --> SPATEM
    T -- "sonst" --> U["undecoded-Zähler"]
    CAM --> OUT["Zusammenfassung +<br/>SQLite + MQTT/HA"]
    DENM --> OUT
    MAPEM --> OUT
    SPATEM --> OUT
```

</details>


## Sicherheitsschichten
![Diagramm 00-architektur-4](diagrams/00-architektur-4.png)

<details><summary>Mermaid-Quelltext</summary>

```mermaid
flowchart LR
    A["Auto-Bruecke"] -- "TLS 1.2 + Passwort<br/>nur Schreibrecht its/…" --> B["Broker"]
    C["Browser"] -- "HTTPS · nur DE-IPs · Basic-Auth" --> D["Dashboard"]
    B --- E["Decoder: lokal gespeichert,<br/>keine Weitergabe an Dritte"]
```

</details>

