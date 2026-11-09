#pragma once
// Hardwarefreie Logik des Auto-Knotens: ITS5-Strom (vom ESP32-C5) -> 802.11p/GeoNetworking/BTP -> Typ-Zaehler -> LoRa-Nutzlast.
// Bewusst ohne Arduino-Abhaengigkeit, damit sie auf dem PC testbar ist (pio test -e native).
#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace its {

enum Kind { K_OTHER = 0, K_CAM, K_DENM, K_MAPEM, K_SPATEM, K_SECURED };

struct Counters {
    uint16_t cam = 0, denm = 0, spatem = 0, mapem = 0, secured = 0, other = 0;
    void add(Kind k) {
        auto inc = [](uint16_t &v) { if (v < 65535) v++; };
        switch (k) {
        case K_CAM: inc(cam); break;
        case K_DENM: inc(denm); break;
        case K_SPATEM: inc(spatem); break;
        case K_MAPEM: inc(mapem); break;
        case K_SECURED: inc(secured); break;
        default: inc(other); break;
        }
    }
    void reset() { *this = Counters(); }
};

// Rahmen vom Sniffer. Zwei Formate (siehe docs/22-plan-verbesserungen.md):
//   ITS5: 'I','T','S','5', sec(4,LE), usec(4,LE), len(2,LE), Nutzlast(len)                          (Kopf 14 Byte)
//   ITS6: 'I','T','S','6', sec(4,LE), usec(4,LE), len(2,LE), rssi(i8), noise(i8), rate(u8), kind(u8), Nutzlast(len)  (Kopf 18 Byte)
//         kind 0 = 802.11-Paket, kind 1 = Statistik: 3 x uint32 LE kumulativ seit Start des Sniffers: rx_err, unicast, dropped
static const size_t ITS5_MAX = 2400;
static const int8_t RSSI_UNKNOWN = 127;
struct SnifferStats { uint32_t rxErr = 0, unicast = 0, dropped = 0; };

class ItsParser {
public:
    // Fuettert ein Byte; true, sobald ein vollstaendiger Rahmen in data()/size() liegt.
    bool feed(uint8_t b) {
        if (pos_ < 3) {
            static const uint8_t magic[3] = {'I', 'T', 'S'};
            if (b == magic[pos_]) { hdr_[pos_++] = b; } else { pos_ = (b == 'I') ? 1 : 0; if (pos_) hdr_[0] = b; }
            return false;
        }
        if (pos_ == 3) {
            if (b == '5' || b == '6') { ver_ = b - '0'; hdr_[pos_++] = b; }
            else { pos_ = (b == 'I') ? 1 : 0; if (pos_) hdr_[0] = b; }
            return false;
        }
        size_t hl = ver_ == 6 ? 18 : 14;
        if (pos_ < hl) {
            hdr_[pos_++] = b;
            if (pos_ == hl) {
                len_ = hdr_[12] | (hdr_[13] << 8);
                got_ = 0;
                if (len_ == 0 || len_ > ITS5_MAX) { pos_ = 0; bad_++; }
            }
            return false;
        }
        buf_[got_++] = b;
        if (got_ == len_) { pos_ = 0; return true; }
        return false;
    }
    const uint8_t *data() const { return buf_; }
    size_t size() const { return len_; }
    uint32_t bad() const { return bad_; }
    int version() const { return ver_; }
    // Felder des letzten vollstaendigen Rahmens (ITS5: unbekannt)
    int8_t rssi() const { return ver_ == 6 ? (int8_t)hdr_[14] : RSSI_UNKNOWN; }
    int8_t noise() const { return ver_ == 6 ? (int8_t)hdr_[15] : RSSI_UNKNOWN; }
    uint8_t rate() const { return ver_ == 6 ? hdr_[16] : 0; }
    bool isStats() const { return ver_ == 6 && hdr_[17] == 1; }
    // Statistikrahmen auslesen; false, wenn der Rahmen keiner ist oder zu kurz
    bool stats(SnifferStats &st) const {
        if (!isStats() || len_ < 12) return false;
        auto g = [&](size_t o) { return (uint32_t)buf_[o] | ((uint32_t)buf_[o + 1] << 8) | ((uint32_t)buf_[o + 2] << 16) | ((uint32_t)buf_[o + 3] << 24); };
        st.rxErr = g(0); st.unicast = g(4); st.dropped = g(8);
        return true;
    }
private:
    uint8_t hdr_[18] = {0};
    uint8_t buf_[ITS5_MAX];
    size_t pos_ = 0, got_ = 0, len_ = 0;
    int ver_ = 5;
    uint32_t bad_ = 0;
};
using Its5Parser = ItsParser;  // alter Name

// Laenge des GeoNetworking-Extended-Headers (ETSI EN 302 636-4-1): HT 1 Beacon, 2 GUC, 3 GAC, 4 GBC,
// 5 TSB (HST 0 = SHB, u.a. CAM: 28 Byte; HST 1 = Multi-Hop: 36), 6 LS. Verifiziert an echten Paketen (Testfahrt 08.11.2026).
static inline int extLen(int ht, int hst = 0) {
    switch (ht) {
    case 1: return 24;
    case 2: return 48;
    case 3: case 4: return 44;
    case 5: return hst == 0 ? 28 : 36;
    case 6: return 36;
    default: return -1;
    }
}

static inline Kind kindFromPort(uint16_t port) {
    switch (port) {
    case 2001: return K_CAM;
    case 2002: return K_DENM;
    case 2003: return K_MAPEM;
    case 2004: return K_SPATEM;
    default: return K_OTHER;
    }
}

// Ab dem Common Header (unsigniert bzw. aus der 1609.2-Huelle entpackt): BTP-B-Port bestimmen.
static inline Kind classifyCommon(const uint8_t *c, size_t n) {
    if (n < 8) return K_OTHER;
    int cnh = c[0] >> 4, ht = c[1] >> 4;
    int el = extLen(ht, c[1] & 0x0F);
    if (el < 0 || cnh != 2) return K_OTHER;  // nur BTP-B
    size_t off = 8 + (size_t)el;
    if (n < off + 4) return K_OTHER;
    return kindFromPort((uint16_t)((c[off] << 8) | c[off + 1]));
}

// OER-Laengenangabe (X.696): <128 ein Byte, sonst 0x80|n gefolgt von n Laengenbytes.
static inline bool oerLen(const uint8_t *p, size_t n, size_t &pos, size_t &len) {
    if (pos >= n) return false;
    uint8_t b = p[pos++];
    if (b < 0x80) { len = b; return true; }
    size_t k = b & 0x7F;
    if (k == 0 || k > 2 || pos + k > n) return false;
    len = 0;
    while (k--) len = (len << 8) | p[pos++];
    return true;
}

// Minimaler Durchgriff durch Ieee1609Dot2Data (OER) bis zu den unsignierten Nutzdaten.
// Erwartet die in Europa uebliche Form signedData{tbsData{payload{data{unsecuredData}}}} (Signatur/Zertifikat werden
// nicht geprueft!) oder direkt unsecuredData. Liefert false, wenn das Layout abweicht -> Aufrufer zaehlt K_SECURED.
static inline bool unwrap1609(const uint8_t *p, size_t n, const uint8_t *&in, size_t &inLen) {
    size_t pos = 0, len = 0;
    if (n < 4 || p[pos++] != 3) return false;                 // protocolVersion 3
    uint8_t tag = p[pos++];
    if (tag == 0x81) {                                        // signedData
        pos++;                                                // hashId
        if (pos >= n) return false;
        uint8_t pre = p[pos++];                               // SignedDataPayload: Bit7 = Extension, Bit6 = data vorhanden
        if (!(pre & 0x40)) return false;
        if (pos + 2 > n || p[pos++] != 3) return false;       // innere Ieee1609Dot2Data
        tag = p[pos++];
    }
    if (tag != 0x80) return false;                            // unsecuredData
    if (!oerLen(p, n, pos, len) || pos + len > n || len < 4) return false;
    in = p + pos;
    inLen = len;
    return true;
}

// Ordnet einen 802.11p-Frame (ohne FCS) einem Nachrichtentyp zu.
// Signierte Pakete (IEEE 1609.2) werden ausgepackt (ohne Signaturpruefung); gelingt das nicht -> K_SECURED.
static inline Kind classify(const uint8_t *f, size_t n) {
    if (n < 24 + 8 + 4) return K_OTHER;
    size_t hdr = (f[0] & 0x80) ? 26 : 24;
    if (n < hdr + 8 + 4) return K_OTHER;
    static const uint8_t llc[8] = {0xAA, 0xAA, 0x03, 0x00, 0x00, 0x00, 0x89, 0x47};
    if (memcmp(f + hdr, llc, 8) != 0) return K_OTHER;
    const uint8_t *gn = f + hdr + 8;
    size_t gl = n - hdr - 8;
    if (gl < 4) return K_OTHER;
    int nh = gn[0] & 0x0F;
    if (nh == 1) return classifyCommon(gn + 4, gl - 4);
    if (nh != 2) return K_OTHER;
    const uint8_t *in; size_t il;
    if (!unwrap1609(gn + 4, gl - 4, in, il)) return K_SECURED;
    Kind k = classifyCommon(in, il);
    if (k == K_OTHER && il >= 4) k = kindFromPort((uint16_t)((in[0] << 8) | in[1]));  // evtl. direkt BTP
    return k == K_OTHER ? K_SECURED : k;
}

// LoRaWAN-Nutzlast v1 (25 Byte, Big Endian). Layout siehe docs/10-lorawan.md
static const size_t PAYLOAD_LEN = 25;
enum Flags : uint8_t { F_GPS_FIX = 1, F_DENM_NEW = 2, F_BRIDGE_ALIVE = 4 };

static inline void put16(uint8_t *p, uint16_t v) { p[0] = v >> 8; p[1] = v & 0xFF; }
static inline void put32(uint8_t *p, int32_t v) { p[0] = (uint32_t)v >> 24; p[1] = (uint32_t)v >> 16; p[2] = (uint32_t)v >> 8; p[3] = (uint32_t)v; }

static inline size_t packPayload(uint8_t *o, const Counters &c, uint8_t flags, int32_t lat_e6, int32_t lon_e6,
                                 uint8_t speed_kmh, uint8_t sats, uint8_t uptime_10min) {
    o[0] = 1;  // Version
    o[1] = flags;
    put32(o + 2, lat_e6);
    put32(o + 6, lon_e6);
    o[10] = speed_kmh;
    o[11] = sats;
    put16(o + 12, c.cam);
    put16(o + 14, c.denm);
    put16(o + 16, c.spatem);
    put16(o + 18, c.mapem);
    put16(o + 20, c.secured);
    put16(o + 22, c.other);
    o[24] = uptime_10min;
    return PAYLOAD_LEN;
}


// LoRaWAN-Nutzlast v2 (36 Byte): v1 (Byte 0 = 2) + Funkstrecke des Sniffers im Sendeintervall.
// 25 rssi_avg (int8, 127 = unbekannt) | 26 rssi_min | 27 rssi_max | 28-29 rx_err | 30-31 unicast | 32-33 dropped | 34-35 lost (je uint16, Differenz im Intervall, gesaettigt)
static const size_t PAYLOAD_LEN_V2 = 36;
struct LinkInfo {
    int8_t rssiAvg = RSSI_UNKNOWN, rssiMin = RSSI_UNKNOWN, rssiMax = RSSI_UNKNOWN;
    uint32_t rxErr = 0, unicast = 0, dropped = 0, lost = 0;
};
static inline uint16_t sat16(uint32_t v) { return v > 0xFFFF ? 0xFFFF : (uint16_t)v; }
static inline size_t packPayloadV2(uint8_t *o, const Counters &c, uint8_t flags, int32_t lat_e6, int32_t lon_e6,
                                   uint8_t speed_kmh, uint8_t sats, uint8_t uptime_10min, const LinkInfo &l) {
    packPayload(o, c, flags, lat_e6, lon_e6, speed_kmh, sats, uptime_10min);
    o[0] = 2;
    o[25] = (uint8_t)l.rssiAvg; o[26] = (uint8_t)l.rssiMin; o[27] = (uint8_t)l.rssiMax;
    put16(o + 28, sat16(l.rxErr)); put16(o + 30, sat16(l.unicast)); put16(o + 32, sat16(l.dropped)); put16(o + 34, sat16(l.lost));
    return PAYLOAD_LEN_V2;
}

}  // namespace its
