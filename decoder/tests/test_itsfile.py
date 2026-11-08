import os, struct, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from its_decoder import itsfile as F

PL = bytes(range(40))


def its5(sec=1, usec=2):
    return b"ITS5" + struct.pack("<IIH", sec, usec, len(PL)) + PL


def its6(rssi, noise=-95, rate=6, kind=0, pl=PL):
    return b"ITS6" + struct.pack("<IIH", 7, 9, len(pl)) + struct.pack("<bbBB", rssi, noise, rate, kind) + pl


def test_mixed_stream():
    stats = its6(127, 127, 0, 1, struct.pack("<III", 3, 260, 65541))
    buf = b"\x00junk" + its5() + its6(-71) + stats + its6(127)
    recs = list(F.iter_records(buf))
    assert [r.version for r in recs] == [5, 6, 6]
    assert recs[0].rssi is None and recs[1].rssi == -71 and recs[1].noise == -95 and recs[1].rate == 6
    assert recs[2].rssi is None
    allr = list(F.iter_records(buf, include_stats=True))
    assert len(allr) == 4 and allr[2].stats() == (3, 260, 65541)


def test_roundtrip_and_pcap():
    r = F.Rec(10, 20, PL, 6, -80, -96, 12)
    back = list(F.iter_records(F.pack(r) + F.pack(F.Rec(11, 0, PL))))
    assert back[0].rssi == -80 and back[0].noise == -96 and back[0].rate == 12 and back[1].rssi is None
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.pcap")
        F.write_pcap(p, back)
        b = open(p, "rb").read()
        assert struct.unpack("<I", b[:4])[0] == 0xA1B2C3D4 and struct.unpack("<I", b[20:24])[0] == 105 and len(b) == 24 + 2 * (16 + 40)


def test_truncated_and_bad_length():
    good = its6(-60)
    assert list(F.iter_records(good[:-5])) == []
    bad = b"ITS6" + struct.pack("<IIH", 1, 1, 9999) + b"\0\0\0\0" + PL
    assert len(list(F.iter_records(bad + good))) == 1
