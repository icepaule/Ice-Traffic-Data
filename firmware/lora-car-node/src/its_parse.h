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

// ITS5-Rahmen: 'I','T','S','5', sec(4,LE), usec(4,LE), len(2,LE), Nutzlast(len)
static const size_t ITS5_MAX = 2400;
class Its5Parser {
public:
    // Fuettert ein Byte; true, sobald ein vollstaendiger Rahmen in data()/size() liegt.
    bool feed(uint8_t b) {
        static const uint8_t magic[4] = {'I', 'T', 'S', '5'};
        if (pos_ < 4) {
            if (b == magic[pos_]) { hdr_[pos_++] = b; } else { pos_ = (b == 'I') ? 1 : 0; if (pos_) hdr_[0] = b; }
            return false;
        }
        if (pos_ < 14) {
            hdr_[pos_++] = b;
            if (pos_ == 14) {
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
private:
    uint8_t hdr_[14] = {0};
    uint8_t buf_[ITS5_MAX];
    size_t pos_ = 0, got_ = 0, len_ = 0;
    uint32_t bad_ = 0;
};

// Laenge des GeoNetworking-Extended-Headers je Header-Type (wie decoder/its_decoder/gn.py)
static inline int extLen(int ht) {
    switch (ht) {
    case 0: return 24;
    case 1: return 48;
    case 2: case 3: return 44;
    case 4: return 28;
    case 5: return 36;
    default: return -1;
    }
}

// Ordnet einen 802.11p-Frame (ohne FCS) einem Nachrichtentyp zu.
// Signierte Pakete (IEEE 1609.2) werden nur als K_SECURED gezaehlt: die Typbestimmung braeuchte die 1609.2-Huelle
// (Entwurf, siehe docs/10-lorawan.md). Die vollstaendige Dekodierung uebernimmt der Heimserver.
static inline Kind classify(const uint8_t *f, size_t n) {
    if (n < 26 + 8 + 4) return K_OTHER;
    size_t hdr = (f[0] & 0x80) ? 26 : 24;
    if (n < hdr + 8 + 4) return K_OTHER;
    static const uint8_t llc[8] = {0xAA, 0xAA, 0x03, 0x00, 0x00, 0x00, 0x89, 0x47};
    if (memcmp(f + hdr, llc, 8) != 0) return K_OTHER;
    const uint8_t *gn = f + hdr + 8;
    size_t gl = n - hdr - 8;
    if (gl < 4) return K_OTHER;
    int nh = gn[0] & 0x0F;
    if (nh == 2) return K_SECURED;
    if (nh != 1) return K_OTHER;
    const uint8_t *c = gn + 4;  // Common Header
    if (gl < 4 + 8) return K_OTHER;
    int cnh = c[0] >> 4, ht = c[1] >> 4;
    int el = extLen(ht);
    if (el < 0 || cnh != 2) return K_OTHER;  // nur BTP-B
    size_t off = 4 + 8 + (size_t)el;
    if (gl < off + 4) return K_OTHER;
    uint16_t port = (uint16_t)((gn[off] << 8) | gn[off + 1]);
    switch (port) {
    case 2001: return K_CAM;
    case 2002: return K_DENM;
    case 2003: return K_MAPEM;
    case 2004: return K_SPATEM;
    default: return K_OTHER;
    }
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

}  // namespace its
