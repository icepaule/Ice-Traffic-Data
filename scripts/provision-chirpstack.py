#!/usr/bin/env python3
"""Legt in ChirpStack v4 Anwendung, Device-Profile (ABP, Einkanal-Gateway) und Geraet 'ice-car' an.
Schluessel bleiben lokal (JSON mit Rechten 600 + secrets.h fuer die Firmware, beide NICHT im Repo).
Nutzung auf dem ChirpStack-Host:  sudo python3 scripts/provision-chirpstack.py [/opt/chirpstack]"""
import base64, hashlib, hmac, json, os, secrets, subprocess, sys, urllib.error, urllib.request, uuid

CS = sys.argv[1] if len(sys.argv) > 1 else "/opt/chirpstack"
HERE = os.path.dirname(os.path.abspath(__file__))
CODEC = os.path.join(HERE, "..", "firmware", "lora-car-node", "chirpstack-codec.js")
SECRETS_H = os.path.join(HERE, "..", "firmware", "lora-car-node", "src", "secrets.h")
BASE = "http://127.0.0.1:8191"
env = dict(l.strip().split("=", 1) for l in open(f"{CS}/.env") if "=" in l and not l.startswith("#"))


def b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def sql(q):
    return subprocess.run(["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "chirpstack", "-d", "chirpstack", "-tA", "-c", q],
                          capture_output=True, text=True, cwd=CS)


key_id = str(uuid.uuid4())
h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
p = b64(json.dumps({"aud": "chirpstack", "iss": "chirpstack", "sub": key_id, "typ": "key"}).encode())
TOKEN = f"{h}.{p}.{b64(hmac.new(env['API_SECRET'].encode(), f'{h}.{p}'.encode(), hashlib.sha256).digest())}"
r = sql(f"insert into api_key(id,created_at,name,is_admin,is_read_only) values ('{key_id}',now(),'ice-traffic-provisioning',true,false);")
assert r.returncode == 0, r.stderr


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "Grpc-Metadata-Authorization": "Bearer " + TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            t = resp.read().decode()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:300]}")


try:
    tenant = call("GET", "/api/tenants?limit=10")["result"][0]["id"]
    prof = dict(tenantId=tenant, name="IceTraffic Car EU868 ABP", description="Auto-Knoten, ABP, Einkanal-Gateway", region="EU868",
                macVersion="LORAWAN_1_0_3", regParamsRevision="A", adrAlgorithmId="default", payloadCodecRuntime="JS",
                payloadCodecScript=open(CODEC).read(), flushQueueOnActivate=True, uplinkInterval=60, deviceStatusReqInterval=0,
                supportsClassB=False, supportsClassC=False, autoDetectMeasurements=False, supportsOtaa=False,
                abpRx1Delay=1, abpRx1DrOffset=0, abpRx2Dr=0, abpRx2Freq=869525000)
    prof_id = call("POST", "/api/device-profiles", {"deviceProfile": prof})["id"]
    app_id = call("POST", "/api/applications", {"application": {"name": "IceTraffic", "description": "Ice-Traffic-Data Auto-Knoten", "tenantId": tenant}})["id"]
    dev = dict(devEui=secrets.token_hex(8), devAddr="00" + secrets.token_hex(3), appSKey=secrets.token_hex(16), nwkSKey=secrets.token_hex(16))
    call("POST", "/api/devices", {"device": {"devEui": dev["devEui"], "name": "ice-car", "description": "Auto-Knoten (ABP)", "applicationId": app_id,
                                              "deviceProfileId": prof_id, "skipFcntCheck": True, "isDisabled": False}})
    call("POST", f"/api/devices/{dev['devEui']}/activate", {"deviceActivation": {"devEui": dev["devEui"], "devAddr": dev["devAddr"], "appSKey": dev["appSKey"],
         "nwkSEncKey": dev["nwkSKey"], "fNwkSIntKey": dev["nwkSKey"], "sNwkSIntKey": dev["nwkSKey"], "fCntUp": 0, "nFCntDown": 0, "aFCntDown": 0}})
    out = f"{CS}/car_device.json"
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(dict(dev, application_id=app_id, profile_id=prof_id), f)
    arr = lambda hx: "{" + ", ".join("0x" + hx[i:i + 2] for i in range(0, len(hx), 2)) + "}"
    fd = os.open(SECRETS_H, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("#pragma once\n#define CAR_SECRETS_CONFIGURED 1\n")
        f.write(f"static const uint32_t CAR_DEV_ADDR = 0x{dev['devAddr']};\n")
        f.write(f"static const uint8_t CAR_NWK_S_KEY[16] = {arr(dev['nwkSKey'])};\n")
        f.write(f"static const uint8_t CAR_APP_S_KEY[16] = {arr(dev['appSKey'])};\n")
    print("provisioniert: Anwendung IceTraffic, Geraet ice-car; Schluessel:", out, "und", os.path.normpath(SECRETS_H))
finally:
    sql(f"delete from api_key where id='{key_id}';")
