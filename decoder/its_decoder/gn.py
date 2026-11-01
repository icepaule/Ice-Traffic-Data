"""802.11p-OCB-Frame -> LLC -> GeoNetworking -> BTP -> Nutzlast (CAM/DENM/SPATEM/MAPEM)."""
import struct
from dataclasses import dataclass, field
from typing import Optional

BTP_PORTS = {2001: "CAM", 2002: "DENM", 2003: "MAPEM", 2004: "SPATEM",
             2005: "SAEM", 2006: "IVIM", 2007: "SREM", 2008: "SSEM", 2009: "CPM"}
# Laenge des Extended Header je Header-Type (HT)
EXT_LEN = {0: 24, 1: 48, 2: 44, 3: 44, 4: 28, 5: 36}


@dataclass
class GnPacket:
    src_mac: str = ""
    gn_addr: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    speed: Optional[float] = None  # m/s (GN-Positionsvektor)
    heading: Optional[float] = None
    ht: int = -1
    secured: bool = False
    port: int = 0
    msg_type: str = ""
    payload: bytes = b""
    notes: list = field(default_factory=list)


def _mac(b):
    return ":".join(f"{x:02x}" for x in b)


def _lpv(g, b):
    addr, _tst, lat, lon, spd, hdg = struct.unpack(">8sIiiHH", b[:24])
    g.gn_addr = addr.hex()
    g.lat, g.lon = lat / 1e7, lon / 1e7
    sp = spd & 0x7FFF
    if sp & 0x4000:  # 15 Bit, Zweierkomplement
        sp -= 0x8000
    g.speed, g.heading = sp * 0.01, hdg * 0.1


def parse_common(g, data):
    """Common Header + Extended Header + BTP-B. Gibt Nutzlast zurueck oder None."""
    if len(data) < 12:
        return None
    nh, ht = data[0] >> 4, data[1] >> 4
    pl = struct.unpack(">H", data[4:6])[0]
    if nh not in (1, 2) or ht not in EXT_LEN:
        return None
    ext = data[8:8 + EXT_LEN[ht]]
    if ht in (1, 2, 3, 4, 5):
        # SN(2)+res(2) vor dem SO-PV, ausser SHB (HST 0 bei HT 4) und Beacon
        off = 0 if (ht == 4 and (data[1] & 0xF) == 0) or ht == 0 else 4
        if len(ext) >= off + 24:
            _lpv(g, ext[off:off + 24])
    g.ht = ht
    rest = data[8 + EXT_LEN[ht]:]
    if nh == 2 and len(rest) >= 4:  # BTP-B
        g.port = struct.unpack(">H", rest[:2])[0]
        g.msg_type = BTP_PORTS.get(g.port, f"port{g.port}")
        g.payload = rest[4:4 + pl - 4] if pl >= 4 else rest[4:]
        return g.payload
    return None


def parse_frame(frame: bytes, sec=None) -> GnPacket:
    g = GnPacket()
    if len(frame) < 26 + 8 + 4:
        g.notes.append("zu kurz")
        return g
    fc = frame[0]
    g.src_mac = _mac(frame[10:16])
    hdr = 26 if (fc & 0x80) else 24  # QoS-Data hat 2 Byte QoS-Control
    llc = frame[hdr:hdr + 8]
    if llc[:6] != b"\xaa\xaa\x03\x00\x00\x00" or llc[6:8] != b"\x89\x47":
        g.notes.append("kein GeoNetworking (Ethertype %s)" % llc[6:8].hex())
        return g
    gn = frame[hdr + 8:]
    if len(gn) < 4:
        return g
    bh_nh = gn[0] & 0xF
    body = gn[4:]
    if bh_nh == 1:
        parse_common(g, body)
    elif bh_nh == 2:
        g.secured = True
        if sec is None:
            g.notes.append("signiert, kein 1609.2-Schema")
            return g
        try:
            msg, _ = sec.decode_with_length("Ieee1609Dot2Data", body)
            content = msg["content"]
            kind, val = content
            inner = None
            if kind == "signedData":
                p = val["tbsData"]["payload"]["data"]["content"]
                inner = p[1] if p[0] == "unsecuredData" else None
            elif kind == "unsecuredData":
                inner = val
            if inner is None:
                g.notes.append("1609.2: keine unsecuredData")
                return g
            if parse_common(g, inner) is None:  # evtl. direkt BTP
                if len(inner) > 4:
                    g.port = struct.unpack(">H", inner[:2])[0]
                    g.msg_type = BTP_PORTS.get(g.port, "")
                    g.payload = inner[4:]
        except Exception as e:  # noqa: BLE001
            g.notes.append(f"1609.2-Fehler: {e}")
    return g
