"""Synthetische ITS-G5-Frames fuer Tests und Demo (kein Ersatz fuer echte Funkdaten)."""
import struct


def lpv(lat, lon, speed=500, heading=900):
    return b"\x00\x00\xaa\xbb\xcc\xdd\xee\xff" + struct.pack(">IiiHH", 1234, int(lat * 1e7), int(lon * 1e7), speed, heading)


def frame(port, payload, lat=48.2, lon=11.65, ht=5, hst=0):  # HT 5 + HST 0 = SHB (wie CAM)
    mac = b"\x02\x00\x00\x00\x00\x01"
    dot11 = b"\x88\x00\x00\x00" + b"\xff" * 6 + mac + b"\xff" * 6 + b"\x00\x00" + b"\x00\x00"
    llc = b"\xaa\xaa\x03\x00\x00\x00\x89\x47"
    basic = bytes([0x11, 0, 5, 1])
    ext = lpv(lat, lon) + (b"\0\0\0\0" if ht == 5 else b"")
    btp = struct.pack(">HH", port, 0) + payload
    common = bytes([0x20, (ht << 4) | hst, 0x50, 0x80]) + struct.pack(">H", len(btp)) + bytes([1, 0])
    return dot11 + llc + basic + common + ext + btp


def cam(schemas, station, lat, lon, speed_ms=13.9, heading_deg=90.0, stype=5):
    return schemas["CAM"].encode("CAM", {
        "header": {"protocolVersion": 2, "messageID": 2, "stationID": station},
        "cam": {"generationDeltaTime": 100, "camParameters": {
            "basicContainer": {"stationType": stype, "referencePosition": {
                "latitude": int(lat * 1e7), "longitude": int(lon * 1e7),
                "positionConfidenceEllipse": {"semiMajorConfidence": 10, "semiMinorConfidence": 10, "semiMajorOrientation": 0},
                "altitude": {"altitudeValue": 5000, "altitudeConfidence": "alt-000-01"}}},
            "highFrequencyContainer": ("basicVehicleContainerHighFrequency", {
                "heading": {"headingValue": int(heading_deg * 10), "headingConfidence": 10},
                "speed": {"speedValue": int(speed_ms * 100), "speedConfidence": 5},
                "driveDirection": "forward",
                "vehicleLength": {"vehicleLengthValue": 45, "vehicleLengthConfidenceIndication": "noTrailerPresent"},
                "vehicleWidth": 18,
                "longitudinalAcceleration": {"longitudinalAccelerationValue": 0, "longitudinalAccelerationConfidence": 10},
                "curvature": {"curvatureValue": 0, "curvatureConfidence": "unavailable"},
                "curvatureCalculationMode": "yawRateUsed",
                "yawRate": {"yawRateValue": 0, "yawRateConfidence": "unavailable"}})}}})


def spatem(schemas, station, intersection, signal_group, state, min_end=120):
    return schemas["SPATEM"].encode("SPATEM", {
        "header": {"protocolVersion": 2, "messageId": 4, "stationId": station},
        "spat": {"intersections": [{
            "id": {"id": intersection}, "revision": 1, "status": (b"\x00\x00", 16),
            "states": [{"signalGroup": signal_group, "state-time-speed": [
                {"eventState": state, "timing": {"minEndTime": min_end}}]}]}]}})


def denm(schemas, station, lat, lon, cause=1, sub=0, seq=1):
    return schemas["DENM"].encode("DENM", {
        "header": {"protocolVersion": 2, "messageID": 1, "stationID": station},
        "denm": {"management": {"actionID": {"originatingStationID": station, "sequenceNumber": seq},
                                "detectionTime": 1000000, "referenceTime": 1000000,
                                "eventPosition": {"latitude": int(lat * 1e7), "longitude": int(lon * 1e7),
                                                  "positionConfidenceEllipse": {"semiMajorConfidence": 10, "semiMinorConfidence": 10, "semiMajorOrientation": 0},
                                                  "altitude": {"altitudeValue": 5000, "altitudeConfidence": "alt-000-01"}},
                                "validityDuration": 600, "stationType": 5},
                 "situation": {"informationQuality": 3, "eventType": {"causeCode": cause, "subCauseCode": sub}}}})


def mapem(schemas, station, intersection, lat, lon):
    return schemas["MAPEM"].encode("MAPEM", {
        "header": {"protocolVersion": 2, "messageId": 5, "stationId": station},
        "map": {"msgIssueRevision": 1, "intersections": [{
            "id": {"id": intersection}, "revision": 1, "refPoint": {"lat": int(lat * 1e7), "long": int(lon * 1e7)}, "laneWidth": 350,
            "laneSet": [{"laneID": 1, "ingressApproach": 1,
                         "laneAttributes": {"directionalUse": (b"\x80", 2), "sharedWith": (b"\x00\x00", 10), "laneType": ("vehicle", (b"\x00", 8))},
                         "nodeList": ("nodes", [{"delta": ("node-XY1", {"x": 0, "y": 100})}, {"delta": ("node-XY1", {"x": 0, "y": 200})}])}]}]}})
