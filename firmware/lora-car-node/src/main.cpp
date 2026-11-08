// ENTWURF (DRAFT) – LoRa-Auto-Knoten: Seeed XIAO ESP32S3 + Wio-SX1262 + Grove GPS (Air530)
// Liest den ITS5-Strom des ESP32-C5 (nur Mithoeren), zaehlt Nachrichtentypen, liest GNSS und sendet
// alle INTERVAL_MS (und bei neuer Gefahrenmeldung) eine 25-Byte-Zusammenfassung per LoRaWAN (ABP, Einkanal-Gateway).
// Noch NICHT auf Hardware getestet. Pins: Meshtastic-Variante seeed_xiao_s3 (Wio-SX1262) – nach Lieferung pruefen.
#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <TinyGPSPlus.h>
#include "eu868_single.h"
#include "its_parse.h"
#include "secrets.h"

#if !defined(CAR_SECRETS_CONFIGURED) || CAR_SECRETS_CONFIGURED != 1
#error "secrets.example.h nach secrets.h kopieren, fuellen und CAR_SECRETS_CONFIGURED auf 1 setzen"
#endif

// --- Pins ---
static const int LORA_SCK = 7, LORA_MISO = 8, LORA_MOSI = 9;                       // SPI
static const int LORA_NSS = 41, LORA_DIO1 = 39, LORA_BUSY = 40, LORA_RESET = 42;   // SX1262
static const int LORA_RXEN = 38;                                                   // HF-Schalter (DIO2 steuert TX)
static const int ITS5_RX = 44;   // D7: Draht vom TX des ESP32-C5 (115200 Baud, 3,3 V)
static const int GPS_RX = 6;     // D5 <- TX des Grove-GPS
static const int GPS_TX = 5;     // D4 -> RX des Grove-GPS

// --- Timing (Duty-Cycle 1 %: bei DR3 und 25 Byte ca. 0,3 s Sendezeit -> >= 30 s Abstand) ---
static const uint32_t INTERVAL_MS = 60000;
static const uint32_t EVENT_MIN_GAP_MS = 30000;

SPIClass loraSpi(FSPI);
SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RESET, LORA_BUSY, loraSpi);
LoRaWANNode node(&radio, &EU868_SINGLE, 0);
TinyGPSPlus gps;
its::Its5Parser parser;
its::Counters counters;
uint32_t lastTx = 0, framesTotal = 0, gpsChars = 0;
bool denmNew = false, loraOk = false;

static void sendSummary() {
    uint8_t flags = 0;
    if (gps.location.isValid() && gps.location.age() < 5000) flags |= its::F_GPS_FIX;
    if (denmNew) flags |= its::F_DENM_NEW;
    if (framesTotal > 0) flags |= its::F_BRIDGE_ALIVE;
    int32_t lat = (flags & its::F_GPS_FIX) ? (int32_t)lround(gps.location.lat() * 1e6) : 0;
    int32_t lon = (flags & its::F_GPS_FIX) ? (int32_t)lround(gps.location.lng() * 1e6) : 0;
    uint8_t spd = gps.speed.isValid() ? (uint8_t)min(255.0, gps.speed.kmph()) : 0;
    uint8_t sat = gps.satellites.isValid() ? (uint8_t)min(255u, (unsigned)gps.satellites.value()) : 0;
    uint8_t up10 = (uint8_t)min(255UL, (unsigned long)(millis() / 600000UL));
    uint8_t buf[its::PAYLOAD_LEN];
    size_t n = its::packPayload(buf, counters, flags, lat, lon, spd, sat, up10);
    Serial.printf("[car] cam=%u denm=%u spat=%u map=%u sec=%u other=%u fix=%d sats=%u\n", counters.cam, counters.denm,
                  counters.spatem, counters.mapem, counters.secured, counters.other, !!(flags & its::F_GPS_FIX), sat);
    Serial.printf("[car] gps chars=%lu sentences=%lu csumfail=%lu\n", (unsigned long)gpsChars, (unsigned long)gps.sentencesWithFix(), (unsigned long)gps.failedChecksum());
    if (loraOk) {
        int16_t st = node.sendReceive(buf, n, 2);  // Port 2; blockiert bis RX-Fenster vorbei (ca. 2 s)
        Serial.printf("[car] lora uplink state=%d\n", (int)st);
    }
    counters.reset();
    denmNew = false;
    lastTx = millis();
}

void setup() {
    Serial.begin(115200);
    delay(3000);
    Serial.println("[car] Ice-Traffic-Data LoRa-Auto-Knoten (DRAFT)");
    Serial1.setRxBufferSize(8192);                        // ITS5-Burst puffern
    Serial1.begin(115200, SERIAL_8N1, ITS5_RX, -1);
    Serial2.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);

    loraSpi.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
    // 868,1 MHz / SF9 / 125 kHz; TCXO 1,8 V an DIO3, DIO2 als HF-Schalter (wie Meshtastic-Variante seeed_xiao_s3)
    int st = radio.begin(868.1, 125.0, 9, 5, RADIOLIB_SX126X_SYNC_WORD_PUBLIC, 10, 8, 1.8, false);
    radio.setRfSwitchPins(LORA_RXEN, RADIOLIB_NC);
    Serial.printf("[car] radio.begin state=%d\n", (int)st);
    if (st == RADIOLIB_ERR_NONE && CAR_DEV_ADDR != 0) {
        node.beginABP(CAR_DEV_ADDR, nullptr, nullptr, CAR_NWK_S_KEY, CAR_APP_S_KEY);  // LoRaWAN 1.0.x: nur NwkSKey
        st = node.activateABP();
        node.setADR(false);
        node.setDatarate(3);
        loraOk = (st == RADIOLIB_ERR_NONE || st == RADIOLIB_LORAWAN_NEW_SESSION || st == RADIOLIB_LORAWAN_SESSION_RESTORED);  // -1118/-1117 = Erfolg
        Serial.printf("[car] activateABP state=%d\n", (int)st);
    } else {
        Serial.println("[car] LoRa AUS (kein DevAddr oder Radio-Fehler) – nur Seriell-Ausgabe");
    }
    lastTx = millis();
}

void loop() {
    // 1) ITS5-Strom
    int budget = 4096;  // pro Durchlauf begrenzen, damit GNSS/Timing nicht verhungern
    while (Serial1.available() && budget-- > 0) {
        if (parser.feed((uint8_t)Serial1.read())) {
            framesTotal++;
            its::Kind k = its::classify(parser.data(), parser.size());
            counters.add(k);
            if (k == its::K_DENM) denmNew = true;
        }
    }
    // 2) GNSS
    while (Serial2.available()) { gps.encode((char)Serial2.read()); gpsChars++; }
    // 3) Senden
    uint32_t now = millis();
    bool due = now - lastTx >= INTERVAL_MS;
    bool event = denmNew && now - lastTx >= EVENT_MIN_GAP_MS;
    if (due || event) sendSummary();
}
