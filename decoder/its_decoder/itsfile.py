"""Mitschnitt-Dateien des Auto-Knotens (frames.bin) lesen/schreiben: Formate ITS5 und ITS6 (gemischt in einer Datei moeglich).

ITS5: 'ITS5', sec(4), usec(4), len(2), Nutzlast                                    (Kopf 14 Byte)
ITS6: 'ITS6', sec(4), usec(4), len(2), rssi(i8), noise(i8), rate(u8), kind(u8), Nutzlast (Kopf 18 Byte)
      kind 0 = 802.11-Paket, kind 1 = Statistik (3 x uint32 LE: rx_err, unicast, dropped)
Siehe docs/22-plan-verbesserungen.md.
"""
import struct
from dataclasses import dataclass
from typing import Iterator, Optional

RSSI_UNKNOWN = 127


@dataclass
class Rec:
    sec: int
    usec: int
    data: bytes
    version: int = 5
    rssi: Optional[int] = None    # dBm, None = unbekannt
    noise: Optional[int] = None
    rate: int = 0
    kind: int = 0                 # 0 Paket, 1 Statistik

    @property
    def ts(self) -> float:
        return self.sec + self.usec / 1e6

    def stats(self):
        """(rx_err, unicast, dropped) bei Statistikrahmen, sonst None"""
        if self.kind != 1 or len(self.data) < 12:
            return None
        return struct.unpack("<III", self.data[:12])


def iter_records(buf: bytes, include_stats: bool = False) -> Iterator[Rec]:
    p, n = 0, len(buf)
    while p + 14 <= n:
        magic = buf[p:p + 4]
        if magic == b"ITS5":
            hl = 14
        elif magic == b"ITS6":
            hl = 18
        else:
            p += 1          # Resync
            continue
        if p + hl > n:
            break
        sec, usec, ln = struct.unpack("<IIH", buf[p + 4:p + 14])
        if ln == 0 or ln > 2400 or p + hl + ln > n:
            p += 1
            continue
        data = buf[p + hl:p + hl + ln]
        if hl == 14:
            r = Rec(sec, usec, data, 5)
        else:
            rssi, noise, rate, kind = struct.unpack("<bbBB", buf[p + 14:p + 18])
            r = Rec(sec, usec, data, 6, None if rssi == RSSI_UNKNOWN else rssi, None if noise == RSSI_UNKNOWN else noise, rate, kind)
        p += hl + ln
        if r.kind == 1 and not include_stats:
            continue
        yield r


def read_file(path: str, include_stats: bool = False) -> Iterator[Rec]:
    with open(path, "rb") as f:
        yield from iter_records(f.read(), include_stats)


def pack(rec: Rec) -> bytes:
    """Datensatz im ITS6-Format serialisieren"""
    return (b"ITS6" + struct.pack("<IIH", rec.sec, rec.usec, len(rec.data)) +
            struct.pack("<bbBB", RSSI_UNKNOWN if rec.rssi is None else rec.rssi, RSSI_UNKNOWN if rec.noise is None else rec.noise, rec.rate, rec.kind) + rec.data)


def write_pcap(path: str, recs) -> None:
    """Pakete als pcap (LINKTYPE 105 = IEEE 802.11) fuer Wireshark; Statistikrahmen werden uebersprungen"""
    with open(path, "wb") as w:
        w.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 105))
        for r in recs:
            if r.kind == 0:
                w.write(struct.pack("<IIII", r.sec, r.usec, len(r.data), len(r.data)) + r.data)
