"""Synthetische Frames: ASN.1-Encode -> 802.11p/GN/BTP verpacken -> Core.feed -> Summary.
Beweist die Konsistenz der Parser-Kette, ersetzt aber KEINE Messung mit echten Funkdaten."""
import struct
import time

from its_decoder.core import Core
from its_decoder.schemas import load

S = load()


def lpv(lat, lon):
    return bytes.fromhex("0000aabbccddeeff"[:16]) + struct.pack(">IiiHH", 1234, int(lat * 1e7), int(lon * 1e7), 500, 900)


def frame(port, payload, ht=5, hst=0, secured_payload=None):
    mac = b"\x02\x00\x00\x00\x00\x01"
    dot11 = b"\x88\x00\x00\x00" + b"\xff" * 6 + mac + b"\xff" * 6 + b"\x00\x00" + b"\x00\x00"
    llc = b"\xaa\xaa\x03\x00\x00\x00\x89\x47"
    basic = bytes([0x11, 0, 5, 1])
    ext = lpv(48.2, 11.65) + (b"\0" * 4 if ht == 5 else b"")
    if ht == 5:
        ext = lpv(48.2, 11.65) + b"\0\0\0\0"
    btp = struct.pack(">HH", port, 0) + payload
    common = bytes([0x20, (ht << 4) | hst, 0x50, 0x80]) + struct.pack(">H", len(btp)) + bytes([1, 0])
    return dot11 + llc + basic + common + ext + btp


def test_cam():
    cam = S["CAM"].encode("CAM", {
        "header": {"protocolVersion": 2, "messageID": 2, "stationID": 4242},
        "cam": {"generationDeltaTime": 100, "camParameters": {
            "basicContainer": {"stationType": 5, "referencePosition": {
                "latitude": 480000000, "longitude": 116000000,
                "positionConfidenceEllipse": {"semiMajorConfidence": 10, "semiMinorConfidence": 10, "semiMajorOrientation": 0},
                "altitude": {"altitudeValue": 5000, "altitudeConfidence": "alt-000-01"}}},
            "highFrequencyContainer": ("basicVehicleContainerHighFrequency", {
                "heading": {"headingValue": 900, "headingConfidence": 10},
                "speed": {"speedValue": 1389, "speedConfidence": 5},
                "driveDirection": "forward",
                "vehicleLength": {"vehicleLengthValue": 45, "vehicleLengthConfidenceIndication": "noTrailerPresent"},
                "vehicleWidth": 18,
                "longitudinalAcceleration": {"longitudinalAccelerationValue": 0, "longitudinalAccelerationConfidence": 10},
                "curvature": {"curvatureValue": 0, "curvatureConfidence": "unavailable"},
                "curvatureCalculationMode": "yawRateUsed",
                "yawRate": {"yawRateValue": 0, "yawRateConfidence": "unavailable"}})}}})
    c = Core(S)
    t, s = c.feed("test", frame(2001, cam))
    assert t == "CAM" and s["station"] == 4242
    assert abs(s["lat"] - 48.0) < 1e-6 and abs(s["speed"] - 13.89) < 0.01
    snap = c.snapshot()
    assert snap["stations"] and snap["gn"][0]["lat"] > 48.19


def test_undecoded_ethertype():
    c = Core(S)
    f = bytearray(frame(2001, b"\0"))
    f[24 + 2 + 7] = 0x00  # kaputter Ethertype
    assert c.feed("t", bytes(f)) is None
    assert c.stats["undecoded"] == 1


def test_spatem():
    spat = S["SPATEM"].encode("SPATEM", {
        "header": {"protocolVersion": 2, "messageId": 4, "stationId": 77},
        "spat": {"intersections": [{
            "id": {"id": 1001}, "revision": 1, "status": (b"\x00\x00", 16),
            "states": [{"signalGroup": 3, "state-time-speed": [
                {"eventState": "protected-Movement-Allowed", "timing": {"minEndTime": 120}}]}]}]}})
    c = Core(S)
    t, s = c.feed("test", frame(2004, spat))
    assert t == "SPATEM"
    g = s["intersections"][0]["groups"][0]
    assert s["intersections"][0]["id"] == 1001 and g["sg"] == 3 and g["min_end"] == 120


def test_secured_wrap():
    """Gleiche CAM in IEEE-1609.2 unsecuredData gepackt (Basic Header NH=2)."""
    sec = S["SEC"]
    if sec is None:
        return
    inner = frame(2001, b"\x00" * 3)  # Platzhalter; nur Huelle pruefen
    common_onwards = inner[24 + 2 + 8 + 4:]
    body = sec.encode("Ieee1609Dot2Data", {"protocolVersion": 3, "content": ("unsecuredData", common_onwards)})
    f = inner[:24 + 2 + 8] + bytes([0x12, 0, 5, 1]) + body
    c = Core(S)
    c.feed("t", f)
    assert c.stats["secured"] == 1


def test_lora_event():
    import json
    from its_decoder import lora
    ev = {"deviceInfo": {"applicationName": "IceTraffic", "deviceName": "ice-car"}, "time": "2026-11-01T12:00:00Z", "fCnt": 7,
          "rxInfo": [{"rssi": -97, "snr": 6.5}],
          "object": {"gps_fix": True, "latitude": 48.1, "longitude": 11.6, "speed_kmh": 50, "satellites": 8,
                     "cam": 12, "denm": 0, "spatem": 3, "mapem": 1, "secured": 40, "other": 2, "denm_new": False, "uptime_min": 30}}
    state, loc = lora.handle_event(json.dumps(ev).encode())
    assert state["cam"] == 12 and state["rssi"] == -97 and loc["latitude"] == 48.1
    ev["deviceInfo"]["applicationName"] = "IceGeiger"
    assert lora.handle_event(json.dumps(ev).encode()) is None
    ev["deviceInfo"]["applicationName"] = "IceTraffic"; ev["object"]["gps_fix"] = False
    assert lora.handle_event(json.dumps(ev).encode())[1] is None
