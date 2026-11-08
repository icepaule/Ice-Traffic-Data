// GPS-LoRa-Knoten: Seeed XIAO ESP32S3 + Wio-SX1262 + Grove GPS (Air530)
// Liest den ITS5-Strom des Traffik-Sniffers (ESP32-C5, nur Mithoeren), zaehlt Nachrichtentypen, liest GNSS und sendet
// alle INTERVAL_MS (und bei neuer Gefahrenmeldung) eine 25-Byte-Zusammenfassung per LoRaWAN (ABP, Einkanal-Gateway).
// Zusaetzlich: eigenes WLAN mit Statusseite (http://192.168.4.1) und lokaler Mitschnitt im Flash (log.csv, frames.bin),
// damit die Fahrt auch ohne LoRa-Gateway-Empfang spaeter ausgewertet werden kann.
#include <Arduino.h>
#include <LittleFS.h>
#include <RadioLib.h>
#include <SPI.h>
#include <TinyGPSPlus.h>
#include <WebServer.h>
#include <WiFi.h>
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
static const int ITS5_RX = 44;   // D7: Draht vom TX des Traffik-Sniffers (115200 Baud, 3,3 V)
static const int GPS_RX = 6;     // D5 <- TX des Grove-GPS
static const int GPS_TX = 5;     // D4 -> RX des Grove-GPS

// --- Timing (Duty-Cycle 1 %: bei DR3 und 25 Byte ca. 0,3 s Sendezeit -> >= 30 s Abstand) ---
static const uint32_t INTERVAL_MS = 60000;
static const uint32_t EVENT_MIN_GAP_MS = 30000;

// --- Lokaler Mitschnitt ---
static const uint32_t LOG_MS = 10000;                 // eine Zeile in log.csv je 10 s
static const size_t FRAMES_MAX_BYTES = 3UL * 1024 * 1024;  // frames.bin deckeln
static const size_t FS_RESERVE = 300UL * 1024;        // Platz im Dateisystem freihalten
static const uint32_t SAMPLE_GAP_MS = 2000;           // CAM/signiert: hoechstens 1 Stichprobe je 2 s und Typ

SPIClass loraSpi(FSPI);
SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RESET, LORA_BUSY, loraSpi);
LoRaWANNode node(&radio, &EU868_SINGLE, 0);
TinyGPSPlus gps;
its::Its5Parser parser;
its::Counters counters;       // Intervall fuer LoRa-Uplink
its::Counters win;            // Intervall fuer log.csv
uint32_t tot[6] = {0};        // Summen seit Start, Index = its::Kind
uint32_t lastTx = 0, lastLog = 0, framesTotal = 0, gpsChars = 0, uplinks = 0, framesSaved = 0;
uint32_t lastSample[6] = {0};
int lastLoraState = 0;
bool denmNew = false, loraOk = false, fsOk = false, logFull = false;
its::Counters lastWin;        // fuer die Statusseite
WebServer web(80);

// --- Zeit aus GPS (UTC) ---
static bool gpsTimeValid() { return gps.date.isValid() && gps.time.isValid() && gps.date.year() >= 2024 && gps.time.age() < 5000; }
static uint32_t gpsUnix() {
    int y = gps.date.year(), m = gps.date.month(), d = gps.date.day();
    y -= m <= 2;
    int era = (y >= 0 ? y : y - 399) / 400;
    unsigned yoe = (unsigned)(y - era * 400);
    unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    long days = (long)era * 146097 + (long)doe - 719468;
    return (uint32_t)(days * 86400L + gps.time.hour() * 3600L + gps.time.minute() * 60L + gps.time.second());
}
static String isoTime() {
    if (!gpsTimeValid()) return String("");
    char b[24];
    snprintf(b, sizeof b, "%04d-%02d-%02dT%02d:%02d:%02dZ", gps.date.year(), gps.date.month(), gps.date.day(),
             gps.time.hour(), gps.time.minute(), gps.time.second());
    return String(b);
}

// --- Mitschnitt ---
static size_t fsFree() { return fsOk ? LittleFS.totalBytes() - LittleFS.usedBytes() : 0; }

static void logLine() {
    if (!fsOk) return;
    if (fsFree() < FS_RESERVE) { logFull = true; return; }
    File f = LittleFS.open("/log.csv", FILE_APPEND);
    if (!f) return;
    bool fix = gps.location.isValid() && gps.location.age() < 5000;
    f.printf("%s,%lu,%d,%.6f,%.6f,%.0f,%u,%u,%u,%u,%u,%u,%u\n", isoTime().c_str(), (unsigned long)(millis() / 1000), fix,
             fix ? gps.location.lat() : 0.0, fix ? gps.location.lng() : 0.0, gps.speed.isValid() ? gps.speed.kmph() : 0.0,
             gps.satellites.isValid() ? (unsigned)gps.satellites.value() : 0u, win.cam, win.denm, win.spatem, win.mapem,
             win.secured, win.other);
    f.close();
}

// Rohframe als ITS5-Rahmen anhaengen (selbes Format wie der Strom des Sniffers -> Decoder kann ihn abspielen).
static void saveFrame(its::Kind k, const uint8_t *d, size_t n) {
    if (!fsOk || logFull || fsFree() < FS_RESERVE) return;
    if (k == its::K_OTHER) return;
    uint32_t now = millis();
    if ((k == its::K_CAM || k == its::K_SECURED) && now - lastSample[k] < SAMPLE_GAP_MS) return;
    lastSample[k] = now;
    File f = LittleFS.open("/frames.bin", FILE_APPEND);
    if (!f) return;
    if (f.size() + 14 + n > FRAMES_MAX_BYTES) { f.close(); return; }
    uint32_t sec = gpsTimeValid() ? gpsUnix() : now / 1000, usec = (now % 1000) * 1000;
    uint8_t h[14] = {'I', 'T', 'S', '5'};
    for (int i = 0; i < 4; i++) { h[4 + i] = sec >> (8 * i); h[8 + i] = usec >> (8 * i); }
    h[12] = n & 0xFF; h[13] = n >> 8;
    f.write(h, 14);
    f.write(d, n);
    f.close();
    framesSaved++;
}

// --- Statusseite ---
static const char PAGE[] PROGMEM = R"HTML(<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ice-Traffic Auto-Knoten</title>
<style>:root{color-scheme:light dark;font-family:system-ui,sans-serif}body{margin:0;padding:16px;max-width:560px;margin:auto}
h1{font-size:1.2rem}table{width:100%;border-collapse:collapse}td{padding:6px 4px;border-bottom:1px solid #8884}td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.ok{color:#2a8}.bad{color:#d54}a,button{font-size:1rem;margin:8px 8px 0 0}</style>
<h1>Ice-Traffic Auto-Knoten</h1><p id=st>Lade …</p>
<table id=t></table>
<p><a href="/log.csv" download>log.csv</a> <a href="/frames.bin" download>frames.bin</a> <button onclick="clr()">Mitschnitt löschen</button></p>
<script>
function row(k,v){return '<tr><td>'+k+'</td><td>'+v+'</td></tr>'}
async function up(){try{const j=await (await fetch('/api')).json();
document.getElementById('st').innerHTML='Uptime '+j.up+' s · Sniffer-Strom: <b class='+(j.frames>0?'ok':'bad')+'>'+(j.frames>0?'empfängt':'KEINE Daten')+'</b>';
let h='';
h+=row('Frames gesamt',j.frames)+row('CAM (seit Start / letzte 10 s)',j.tot.cam+' / '+j.win.cam)+row('DENM',j.tot.denm+' / '+j.win.denm)+row('SPATEM',j.tot.spatem+' / '+j.win.spatem)+row('MAPEM',j.tot.mapem+' / '+j.win.mapem)+row('Signiert (nicht lesbar)',j.tot.sec+' / '+j.win.sec)+row('Sonstige',j.tot.other+' / '+j.win.other);
h+=row('GPS',j.fix?('<span class=ok>Fix</span> '+j.lat.toFixed(5)+', '+j.lon.toFixed(5)):'<span class=bad>kein Fix</span>')+row('Satelliten / km/h',j.sats+' / '+j.kmh)+row('UTC',j.utc||'–');
h+=row('LoRa',(j.lora?'<span class=ok>aktiv</span>':'<span class=bad>aus</span>')+', Uplinks '+j.uplinks+', Status '+j.lst);
h+=row('Mitschnitt',(j.logfull?'<span class=bad>Speicher voll</span> ':'')+'log '+j.logb+' B, frames '+j.frb+' B ('+j.saved+' neu), frei '+Math.round(j.free/1024)+' kB');
document.getElementById('t').innerHTML=h}catch(e){document.getElementById('st').textContent='keine Verbindung'}}
async function clr(){if(confirm('Mitschnitt wirklich löschen?')){await fetch('/clear',{method:'POST'});up()}}
up();setInterval(up,2000)
</script></html>)HTML";

static size_t fileSize(const char *p) {
    if (!fsOk || !LittleFS.exists(p)) return 0;
    File f = LittleFS.open(p, "r");
    size_t n = f ? f.size() : 0;
    if (f) f.close();
    return n;
}

static void handleApi() {
    bool fix = gps.location.isValid() && gps.location.age() < 5000;
    char b[640];
    snprintf(b, sizeof b,
             "{\"up\":%lu,\"frames\":%lu,\"tot\":{\"cam\":%lu,\"denm\":%lu,\"spatem\":%lu,\"mapem\":%lu,\"sec\":%lu,\"other\":%lu},"
             "\"win\":{\"cam\":%u,\"denm\":%u,\"spatem\":%u,\"mapem\":%u,\"sec\":%u,\"other\":%u},"
             "\"fix\":%d,\"lat\":%.6f,\"lon\":%.6f,\"sats\":%u,\"kmh\":%.0f,\"utc\":\"%s\","
             "\"lora\":%d,\"uplinks\":%lu,\"lst\":%d,\"logfull\":%d,\"logb\":%u,\"frb\":%u,\"saved\":%lu,\"free\":%u}",
             (unsigned long)(millis() / 1000), (unsigned long)framesTotal, (unsigned long)tot[its::K_CAM],
             (unsigned long)tot[its::K_DENM], (unsigned long)tot[its::K_SPATEM], (unsigned long)tot[its::K_MAPEM],
             (unsigned long)tot[its::K_SECURED], (unsigned long)tot[its::K_OTHER], lastWin.cam, lastWin.denm, lastWin.spatem,
             lastWin.mapem, lastWin.secured, lastWin.other, fix, fix ? gps.location.lat() : 0.0, fix ? gps.location.lng() : 0.0,
             gps.satellites.isValid() ? (unsigned)gps.satellites.value() : 0u, gps.speed.isValid() ? gps.speed.kmph() : 0.0,
             isoTime().c_str(), loraOk, (unsigned long)uplinks, lastLoraState, logFull, (unsigned)fileSize("/log.csv"),
             (unsigned)fileSize("/frames.bin"), (unsigned long)framesSaved, (unsigned)fsFree());
    web.send(200, "application/json", b);
}

static void sendFile(const char *path, const char *type) {
    if (!fsOk || !LittleFS.exists(path)) { web.send(404, "text/plain", "leer"); return; }
    File f = LittleFS.open(path, "r");
    web.sendHeader("Content-Disposition", String("attachment; filename=") + (path + 1));
    web.streamFile(f, type);
    f.close();
}

static void webSetup() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(CAR_AP_SSID, CAR_AP_PASS, 6, 0, 4);
    web.on("/", []() { web.send_P(200, "text/html; charset=utf-8", PAGE); });
    web.on("/api", handleApi);
    web.on("/log.csv", []() { sendFile("/log.csv", "text/csv"); });
    web.on("/frames.bin", []() { sendFile("/frames.bin", "application/octet-stream"); });
    web.on("/clear", HTTP_POST, []() {
        if (fsOk) { LittleFS.remove("/log.csv"); LittleFS.remove("/frames.bin"); }
        logFull = false;
        framesSaved = 0;
        web.send(200, "text/plain", "ok");
    });
    web.begin();
    Serial.printf("[car] WLAN-AP '%s' -> http://%s\n", CAR_AP_SSID, WiFi.softAPIP().toString().c_str());
}

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
        lastLoraState = st;
        uplinks++;
        Serial.printf("[car] lora uplink state=%d\n", (int)st);
    }
    counters.reset();
    denmNew = false;
    lastTx = millis();
}

void setup() {
    Serial.begin(115200);
    delay(3000);
    Serial.println("[car] Ice-Traffic-Data GPS-LoRa-Knoten");
    fsOk = LittleFS.begin(true);
    Serial.printf("[car] LittleFS %s, frei %u kB\n", fsOk ? "ok" : "FEHLER", (unsigned)(fsFree() / 1024));
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
    webSetup();
    lastTx = lastLog = millis();
}

void loop() {
    // 1) ITS5-Strom
    int budget = 4096;  // pro Durchlauf begrenzen, damit GNSS/Timing nicht verhungern
    while (Serial1.available() && budget-- > 0) {
        if (parser.feed((uint8_t)Serial1.read())) {
            framesTotal++;
            its::Kind k = its::classify(parser.data(), parser.size());
            counters.add(k);
            win.add(k);
            if (tot[k] < 0xFFFFFFFF) tot[k]++;
            if (k == its::K_DENM) denmNew = true;
            saveFrame(k, parser.data(), parser.size());
        }
    }
    // 2) GNSS
    while (Serial2.available()) { gps.encode((char)Serial2.read()); gpsChars++; }
    // 3) Webserver
    web.handleClient();
    // 4) Mitschnitt
    uint32_t now = millis();
    if (now - lastLog >= LOG_MS) {
        logLine();
        lastWin = win;
        win.reset();
        lastLog = now;
    }
    // 5) Senden
    bool due = now - lastTx >= INTERVAL_MS;
    bool event = denmNew && now - lastTx >= EVENT_MIN_GAP_MS;
    if (due || event) sendSummary();
}
