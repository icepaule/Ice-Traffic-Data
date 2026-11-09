// GPS-LoRa-Knoten: Seeed XIAO ESP32S3 + Wio-SX1262 + Grove GPS (Air530)
// Liest den ITS5/ITS6-Strom des Traffik-Sniffers (ESP32-C5, nur Mithoeren), zaehlt Nachrichtentypen, liest GNSS und sendet
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
static const int ITS5_RX = 44;   // D7: Draht vom TX des Traffik-Sniffers (3,3 V)
#ifndef ITS_BAUD
#define ITS_BAUD 921600          // wie der Sniffer (V3); per -DITS_BAUD=115200 auf den alten Wert zurueck
#endif
static const int GPS_RX = 6;     // D5 <- TX des Grove-GPS
static const int GPS_TX = 5;     // D4 -> RX des Grove-GPS

// --- Timing (Duty-Cycle 1 %: bei DR3 und 25 Byte ca. 0,3 s Sendezeit -> >= 30 s Abstand) ---
static const uint32_t INTERVAL_MS = 60000;
static const uint32_t EVENT_MIN_GAP_MS = 30000;

// --- Lokaler Mitschnitt ---
static const uint32_t LOG_MS = 10000;                 // eine Zeile in log.csv je 10 s
static const size_t FRAMES_MAX_BYTES = 4UL * 1024 * 1024;  // frames.bin deckeln (V1: alle Pakete, keine Stichprobe mehr)
static const size_t FS_RESERVE = 300UL * 1024;        // Platz im Dateisystem freihalten
// Flash-Schreiben legt den Prozessor fuer einige 10 ms lahm; in dieser Zeit laeuft der UART-FIFO (128 Byte) ueber und Pakete gehen
// verloren (am 09.11.2026 gemessen: schon bei 50 Paketen/s ca. 25 % Verlust, wenn waehrend des Empfangs geschrieben wird).
// Darum: Pakete in einem grossen RAM-Puffer (PSRAM, sonst 32 kB) sammeln und NUR in Empfangspausen ins Flash schreiben.
static const size_t WBUF_PSRAM = 1024UL * 1024;       // 1 MB im PSRAM (ca. 2600 Pakete)
static const size_t WBUF_INTERN = 32UL * 1024;        // Rueckfall ohne PSRAM
static const uint32_t IDLE_MS = 3000;                 // so lange kein UART-Byte = Pause, Schreiben erlaubt (Schreiben haelt den UART-Interrupt an: nur bei Ruhe)
static const uint32_t FORCE_FLUSH_MS = 600000;        // spaetestens nach 10 min schreiben, auch ohne Pause (Schreiben waehrend des Empfangs kostet Pakete; Stromausfall: hoechstens 10 min Verlust bei Dauerverkehr)

SPIClass loraSpi(FSPI);
SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RESET, LORA_BUSY, loraSpi);
LoRaWANNode node(&radio, &EU868_SINGLE, 0);
TinyGPSPlus gps;
its::ItsParser parser;
its::Counters counters;       // Intervall fuer LoRa-Uplink
its::Counters win;            // Intervall fuer log.csv
uint32_t tot[6] = {0};        // Summen seit Start, Index = its::Kind
uint32_t lastTx = 0, lastLog = 0, framesTotal = 0, gpsChars = 0, uplinks = 0, framesSaved = 0;
// V2/V3/V4: Feldstaerke je 10-s-Fenster und Zaehler des Sniffers (kumulativ, ab Sniffer-Start)
int32_t rssiSum = 0; uint32_t rssiN = 0; int8_t rssiMin = 127, rssiMax = -128; int8_t lastRssiAvg = 127;
its::SnifferStats stats, statsAtLog; bool statsSeen = false;
uint32_t badAtLog = 0, framesLost = 0, itsV6 = 0;
static uint8_t *wbuf = nullptr; size_t wcap = 0, wlen = 0; uint32_t lastFlush = 0, lastRx = 0, flushN = 0, flushMaxMs = 0; size_t framesFileBytes = 0; bool storeOk = true;
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

// Delta eines kumulativen Zaehlers; sinkt er (Sniffer neu gestartet), zaehlt der neue Wert
static uint32_t delta(uint32_t cur, uint32_t prev) { return cur >= prev ? cur - prev : cur; }

// Logzeilen werden im RAM gesammelt und nur in Empfangspausen ins Flash geschrieben (jede Schreib-Operation stoppt den UART-Interrupt;
// ein FIFO-Ueberlauf verwirft im Arduino-Treiber den ganzen Empfangspuffer). Eine Zeile je 10 s, Schreiben hoechstens alle 60 s.
static char lbuf[8192];
static size_t llen = 0;
static uint32_t lastLogFlush = 0;

static void flushLog() {
    if (!llen) return;
    if (fsOk) {
        storeOk = fsFree() >= FS_RESERVE;
        if (!storeOk) logFull = true;
        else {
            File f = LittleFS.open("/log.csv", FILE_APPEND);
            if (f) { f.write((const uint8_t *)lbuf, llen); f.close(); }
        }
    }
    llen = 0;
    lastLogFlush = millis();
}

static void logLine() {
    if (!fsOk || logFull) return;
    char l[320];
    bool fix = gps.location.isValid() && gps.location.age() < 5000;
    int n = snprintf(l, sizeof l, "%s,%lu,%d,%.6f,%.6f,%.0f,%u,%u,%u,%u,%u,%u,%u", isoTime().c_str(), (unsigned long)(millis() / 1000), fix,
                     fix ? gps.location.lat() : 0.0, fix ? gps.location.lng() : 0.0, gps.speed.isValid() ? gps.speed.kmph() : 0.0,
                     gps.satellites.isValid() ? (unsigned)gps.satellites.value() : 0u, win.cam, win.denm, win.spatem, win.mapem,
                     win.secured, win.other);
    // Spalten 14-20: rssi_avg, rssi_min, rssi_max (leer ohne ITS6), rx_err, unicast, dropped, bad (je Fenster)
    if (rssiN) n += snprintf(l + n, sizeof l - n, ",%d,%d,%d", (int)lround((double)rssiSum / rssiN), (int)rssiMin, (int)rssiMax); else n += snprintf(l + n, sizeof l - n, ",,,");
    n += snprintf(l + n, sizeof l - n, ",%lu,%lu,%lu,%lu\n", (unsigned long)delta(stats.rxErr, statsAtLog.rxErr), (unsigned long)delta(stats.unicast, statsAtLog.unicast),
                  (unsigned long)delta(stats.dropped, statsAtLog.dropped), (unsigned long)(parser.bad() - badAtLog));
    if (n > 0 && llen + n < sizeof lbuf) { memcpy(lbuf + llen, l, n); llen += n; }
    if (rssiN) lastRssiAvg = (int8_t)lround((double)rssiSum / rssiN);   // letzten bekannten Wert behalten
    rssiSum = 0; rssiN = 0; rssiMin = 127; rssiMax = -128;
    statsAtLog = stats; badAtLog = parser.bad();
}

// RAM-Puffer ins Flash schreiben, hoechstens maxBytes je Aufruf (0 = alles). Kleine Haeppchen (ca. 4 kB, einige 10 ms), damit
// zwischendurch wieder der UART bedient wird: ein Schreibvorgang des ganzen Puffers dauerte bis zu 3 s (gemessen).
// UART-Fehler (Diagnose): FIFO-Ueberlauf (Hardware, 128 Byte) und voller Ringpuffer; laengste Pausen der Hauptschleife
volatile uint8_t phase = 0;   // 0 Leerlauf, 1 Flash-Haeppchen, 2 Logzeile, 3 LoRa-Senden, 4 Webserver
volatile uint32_t ovfPhase[5] = {0};
volatile uint32_t uartFifoOvf = 0, uartBufFull = 0, uartOther = 0, uartBreak = 0, uartParity = 0, uartFrame = 0;
uint32_t loopMaxMs = 0, lastLoopMs = 0, summaryMaxMs = 0, webMaxMs = 0, logMaxMs = 0;
static size_t wrd = 0;   // bis hierhin schon im Flash
static uint32_t flushByIdle = 0, flushByDrain = 0, drainSet = 0;
static bool draining = false;   // dringendes Leeren des Puffers laeuft
static void flushFrames(size_t maxBytes = 0) {
    if (wlen <= wrd) { wlen = wrd = 0; return; }
    uint32_t t0 = millis();
    size_t n = wlen - wrd;
    if (maxBytes && n > maxBytes) n = maxBytes;
    if (fsOk && !logFull && storeOk) {
        // Freier Platz wird nur in logLine() geprueft (alle 10 s): fsFree() durchlaeuft das Dateisystem und kostete je Haeppchen 100-200 ms
        if (framesFileBytes + n > FRAMES_MAX_BYTES) { storeOk = false; }
        else {
            File f = LittleFS.open("/frames.bin", FILE_APPEND);
            if (f) {
                size_t w = f.write(wbuf + wrd, n);
                framesFileBytes = f.size();
                f.close();
                if (w < n) storeOk = false;   // Schreibfehler (voll)
            }
        }
    }
    wrd += n;
    if (wrd >= wlen) wlen = wrd = 0;
    lastFlush = millis();
    flushN++;
    if (lastFlush - t0 > flushMaxMs) flushMaxMs = lastFlush - t0;
}

// Rohframe als ITS6-Rahmen in den RAM-Puffer (V1: jedes Paket, V2: mit RSSI/Rauschen/Rate); der Decoder kann die Datei abspielen.
static void saveFrame(const uint8_t *d, size_t n, int8_t rssi, int8_t noise, uint8_t rate) {
    if (!fsOk || logFull || !storeOk) { framesLost++; return; }
    size_t rec = 18 + n;
    if (wlen + rec > wcap && wrd > 0) { memmove(wbuf, wbuf + wrd, wlen - wrd); wlen -= wrd; wrd = 0; }   // Platz schaffen
    if (wlen + rec > wcap) flushFrames();   // Notfall: Puffer voll
    if (!storeOk || wlen + rec > wcap) { framesLost++; return; }
    uint32_t now = millis();
    uint32_t sec = gpsTimeValid() ? gpsUnix() : now / 1000, usec = (now % 1000) * 1000;
    uint8_t *h = wbuf + wlen;
    h[0] = 'I'; h[1] = 'T'; h[2] = 'S'; h[3] = '6';
    for (int i = 0; i < 4; i++) { h[4 + i] = sec >> (8 * i); h[8 + i] = usec >> (8 * i); }
    h[12] = n & 0xFF; h[13] = n >> 8;
    h[14] = (uint8_t)rssi; h[15] = (uint8_t)noise; h[16] = rate; h[17] = 0;
    memcpy(h + 18, d, n);
    wlen += rec;
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
h+=row('Frames gesamt',j.frames)+row('CAM (seit Start / letzte 10 s)',j.tot.cam+' / '+j.win.cam)+row('DENM',j.tot.denm+' / '+j.win.denm)+row('SPATEM',j.tot.spatem+' / '+j.win.spatem)+row('MAPEM',j.tot.mapem+' / '+j.win.mapem)+row('Signiert, Hülle nicht lesbar',j.tot.sec+' / '+j.win.sec)+row('Sonstige',j.tot.other+' / '+j.win.other);
h+=row('GPS',j.fix?('<span class=ok>Fix</span> '+j.lat.toFixed(5)+', '+j.lon.toFixed(5)):'<span class=bad>kein Fix</span>')+row('Satelliten / km/h',j.sats+' / '+j.kmh)+row('UTC',j.utc||'–');
h+=row('LoRa',(j.lora?'<span class=ok>aktiv</span>':'<span class=bad>aus</span>')+', Uplinks '+j.uplinks+', Status '+j.lst);
h+=row('Feldstärke (letztes Fenster)',j.rssi>=127?'– (kein ITS6)':j.rssi+' dBm')+row('Sniffer: Fehlerpakete / Unicast / verloren',j.rxerr+' / '+j.uni+' / '+j.drop)+row('Ungültige Rahmen / nicht gespeichert',j.bad+' / '+j.lost);
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
    char b[1800];
    snprintf(b, sizeof b,
             "{\"up\":%lu,\"frames\":%lu,\"tot\":{\"cam\":%lu,\"denm\":%lu,\"spatem\":%lu,\"mapem\":%lu,\"sec\":%lu,\"other\":%lu},"
             "\"win\":{\"cam\":%u,\"denm\":%u,\"spatem\":%u,\"mapem\":%u,\"sec\":%u,\"other\":%u},"
             "\"fix\":%d,\"lat\":%.6f,\"lon\":%.6f,\"sats\":%u,\"kmh\":%.0f,\"utc\":\"%s\","
             "\"lora\":%d,\"uplinks\":%lu,\"lst\":%d,\"logfull\":%d,\"logb\":%u,\"frb\":%u,\"saved\":%lu,\"free\":%u,"
             "\"rssi\":%d,\"rxerr\":%lu,\"uni\":%lu,\"drop\":%lu,\"bad\":%lu,\"lost\":%lu,\"its6\":%lu,\"wbuf\":%u,\"wcap\":%u,\"flushn\":%lu,\"flushmax\":%lu,\"ovf\":%lu,\"bufull\":%lu,\"uerr\":%lu,\"loopmax\":%lu,\"summax\":%lu,\"webmax\":%lu,\"logmax\":%lu,\"ovfp\":[%lu,%lu,%lu,%lu,%lu],\"ebreak\":%lu,\"epar\":%lu,\"eframe\":%lu,\"fidle\":%lu,\"fdrain\":%lu,\"drset\":%lu}",
             (unsigned long)(millis() / 1000), (unsigned long)framesTotal, (unsigned long)tot[its::K_CAM],
             (unsigned long)tot[its::K_DENM], (unsigned long)tot[its::K_SPATEM], (unsigned long)tot[its::K_MAPEM],
             (unsigned long)tot[its::K_SECURED], (unsigned long)tot[its::K_OTHER], lastWin.cam, lastWin.denm, lastWin.spatem,
             lastWin.mapem, lastWin.secured, lastWin.other, fix, fix ? gps.location.lat() : 0.0, fix ? gps.location.lng() : 0.0,
             gps.satellites.isValid() ? (unsigned)gps.satellites.value() : 0u, gps.speed.isValid() ? gps.speed.kmph() : 0.0,
             isoTime().c_str(), loraOk, (unsigned long)uplinks, lastLoraState, logFull, (unsigned)(fileSize("/log.csv") + llen),
             (unsigned)(fileSize("/frames.bin") + (wlen - wrd)), (unsigned long)framesSaved, (unsigned)fsFree(), (int)lastRssiAvg,
             (unsigned long)stats.rxErr, (unsigned long)stats.unicast, (unsigned long)stats.dropped, (unsigned long)parser.bad(),
             (unsigned long)framesLost, (unsigned long)itsV6, (unsigned)(wlen - wrd), (unsigned)wcap, (unsigned long)flushN, (unsigned long)flushMaxMs, (unsigned long)uartFifoOvf, (unsigned long)uartBufFull, (unsigned long)uartOther,
             (unsigned long)loopMaxMs, (unsigned long)summaryMaxMs, (unsigned long)webMaxMs, (unsigned long)logMaxMs,
             (unsigned long)ovfPhase[0], (unsigned long)ovfPhase[1], (unsigned long)ovfPhase[2], (unsigned long)ovfPhase[3], (unsigned long)ovfPhase[4], (unsigned long)uartBreak, (unsigned long)uartParity, (unsigned long)uartFrame, (unsigned long)flushByIdle, (unsigned long)flushByDrain, (unsigned long)drainSet);
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
    web.on("/log.csv", []() { flushLog(); sendFile("/log.csv", "text/csv"); });
    web.on("/frames.bin", []() { flushFrames(); sendFile("/frames.bin", "application/octet-stream"); });
    web.on("/clear", HTTP_POST, []() {
        wlen = wrd = 0; llen = 0;
        if (fsOk) { LittleFS.remove("/log.csv"); LittleFS.remove("/frames.bin"); }
        logFull = false; storeOk = true; framesFileBytes = 0; framesLost = 0;
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
    Serial.printf("[car] sniffer: rssi=%d dBm rx_err=%lu unicast=%lu dropped=%lu bad=%lu lost=%lu its6=%lu\n", (int)lastRssiAvg, (unsigned long)stats.rxErr,
                  (unsigned long)stats.unicast, (unsigned long)stats.dropped, (unsigned long)parser.bad(), (unsigned long)framesLost, (unsigned long)itsV6);
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
    wbuf = (uint8_t *)(psramFound() ? ps_malloc(WBUF_PSRAM) : malloc(WBUF_INTERN));
    wcap = wbuf ? (psramFound() ? WBUF_PSRAM : WBUF_INTERN) : 0;
    Serial.printf("[car] Schreibpuffer %u kB (%s)\n", (unsigned)(wcap / 1024), psramFound() ? "PSRAM" : "intern");
    Serial1.setRxBufferSize(65536);                       // Bursts puffern (LoRa-Senden blockiert ca. 2 s, Flash-Schreiben einige 10 ms)
    Serial1.onReceiveError([](hardwareSerial_error_t e) {
        if (e == UART_FIFO_OVF_ERROR) { uartFifoOvf++; ovfPhase[phase]++; } else if (e == UART_BUFFER_FULL_ERROR) uartBufFull++;
        else { uartOther++; if (e == UART_BREAK_ERROR) uartBreak++; else if (e == UART_PARITY_ERROR) uartParity++; else if (e == UART_FRAME_ERROR) uartFrame++; }
    });
    Serial1.begin(ITS_BAUD, SERIAL_8N1, ITS5_RX, -1);
    framesFileBytes = fileSize("/frames.bin");
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
    lastTx = lastLog = lastFlush = millis();
}

void loop() {
    // 1) ITS5/ITS6-Strom
    int budget = 16384;  // pro Durchlauf begrenzen, damit GNSS/Timing nicht verhungern
    static uint8_t rx[1024];
    int avail;
    while ((avail = Serial1.available()) > 0 && budget > 0) {   // blockweise lesen: Byte fuer Byte ist bei 921600 Baud zu langsam
        int n = Serial1.readBytes(rx, avail > (int)sizeof rx ? (int)sizeof rx : avail);
        budget -= n;
        lastRx = millis();
        for (int i = 0; i < n; i++) {
            if (!parser.feed(rx[i])) continue;
            if (parser.isStats()) {  // Statistikrahmen des Sniffers (kein Paket)
                if (parser.stats(stats)) statsSeen = true;
                continue;
            }
            framesTotal++;
            if (parser.version() == 6) itsV6++;
            int8_t rssi = parser.rssi();
            if (rssi != its::RSSI_UNKNOWN) { rssiSum += rssi; rssiN++; if (rssi < rssiMin) rssiMin = rssi; if (rssi > rssiMax) rssiMax = rssi; }
            its::Kind k = its::classify(parser.data(), parser.size());
            counters.add(k);
            win.add(k);
            if (tot[k] < 0xFFFFFFFF) tot[k]++;
            if (k == its::K_DENM) denmNew = true;
            saveFrame(parser.data(), parser.size(), rssi, parser.noise(), parser.rate());
        }
    }
    // 2) GNSS
    while (Serial2.available()) { gps.encode((char)Serial2.read()); gpsChars++; }
    // 3) Webserver
    { phase = 4; uint32_t t0 = millis(); web.handleClient(); uint32_t d = millis() - t0; if (d > webMaxMs) webMaxMs = d; phase = 0; }
    // 4) Mitschnitt
    uint32_t now = millis();
    bool idle = now - lastRx >= IDLE_MS;
    if (wlen > wrd) {
        // dringend (Puffer fast voll oder 60 s ohne Schreiben): Haeppchen fuer Haeppchen bis leer, dazwischen wird der UART bedient;
        // ein einziges grosses Schreiben hielt die Firmware bis zu 11 s an (gemessen)
        if (!draining && ((wlen - wrd) * 10 >= wcap * 9 || now - lastFlush >= FORCE_FLUSH_MS)) { draining = true; drainSet++; }   // Rueckstand, nicht Fuellstand (wlen enthaelt schon Geschriebenes)
        if (draining || idle) {
            if (draining) flushByDrain++; else flushByIdle++;
            phase = 1; flushFrames(4096); phase = 0;
            // Nach dem Schreiben (Interrupts stehen waehrend des Schreibens still, ankommende Pakete koennen verloren gehen) ist die Leitung
            // nicht mehr "ruhig": erst nach weiteren 300 ms ohne Daten das naechste Haeppchen, sonst wuerden Schreibvorgaenge hintereinander
            // einen ganzen Paketstrom verschlucken
            lastRx = millis() - IDLE_MS + 300;
        }
    } else draining = false;
    if (now - lastLog >= LOG_MS) {   // Logzeile nur im RAM (kein Flash-Zugriff)
        logLine();
        lastWin = win;
        win.reset();
        lastLog = now;
    }
    if (llen && ((idle && now - lastLogFlush >= 60000) || llen > 6000 || now - lastLogFlush >= 300000)) {
        phase = 2; uint32_t t0 = millis(); flushLog(); uint32_t d = millis() - t0; if (d > logMaxMs) logMaxMs = d; phase = 0;
        lastRx = millis() - IDLE_MS + 300;
    }
    // 5) Senden
    bool due = now - lastTx >= INTERVAL_MS;
    bool event = denmNew && now - lastTx >= EVENT_MIN_GAP_MS;
    if (due || event) { phase = 3; uint32_t t0 = millis(); sendSummary(); phase = 0; uint32_t d = millis() - t0; if (d > summaryMaxMs) summaryMaxMs = d; }
    { uint32_t n2 = millis(); if (lastLoopMs && n2 - lastLoopMs > loopMaxMs) loopMaxMs = n2 - lastLoopMs; lastLoopMs = n2; }
}
