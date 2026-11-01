#!/usr/bin/env python3
"""Simuliert einen LoRaWAN-Uplink des Auto-Knotens OHNE Hardware (Ende-zu-Ende-Test der Kette
Gateway -> ChirpStack (MIC, Codec) -> MQTT -> Decoder -> Home Assistant).
Baut ein gueltiges LoRaWAN-1.0.x-Paket mit den echten ABP-Schluesseln und schickt es als Semtech-UDP (PUSH_DATA)
an den Gateway-Bridge-Port. Achtung: das Ergebnis erscheint in ChirpStack/HA wie ein echter Uplink.
Nutzung: python3 scripts/simulate-uplink.py /opt/chirpstack/car_device.json [fcnt] [host] [gateway-eui-hex]"""
import base64, json, socket, struct, sys, time

from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

keys = json.load(open(sys.argv[1]))
fcnt = int(sys.argv[2]) if len(sys.argv) > 2 else int(time.time()) % 60000
host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
gw = bytes.fromhex(sys.argv[4]) if len(sys.argv) > 4 else bytes.fromhex("b0b21cfffe5079a0")
devaddr = int(keys["devAddr"], 16)
nwk, app = bytes.fromhex(keys["nwkSKey"]), bytes.fromhex(keys["appSKey"])


def aes_ecb(key, block):
    e = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return e.update(block) + e.finalize()


def payload_v1():  # wie firmware/lora-car-node/src/its_parse.h packPayload()
    p = bytearray(25)
    p[0] = 1; p[1] = 1 | 4                                   # GNSS-Fix, Bruecke aktiv
    struct.pack_into(">i", p, 2, 48173500); struct.pack_into(">i", p, 6, 11546000)
    p[10] = 42; p[11] = 9
    for off, v in zip(range(12, 24, 2), (37, 0, 6, 1, 52, 3)):  # cam denm spatem mapem secured other
        struct.pack_into(">H", p, off, v)
    p[24] = 3
    return bytes(p)


def encrypt(data):  # LoRaWAN 1.0.x FRMPayload (AppSKey), Uplink
    out = bytearray()
    for i in range((len(data) + 15) // 16):
        a = bytes([0x01, 0, 0, 0, 0, 0]) + struct.pack("<I", devaddr) + struct.pack("<I", fcnt) + bytes([0, i + 1])
        s = aes_ecb(app, a)
        out += bytes(x ^ y for x, y in zip(data[i * 16:(i + 1) * 16], s))
    return bytes(out)


frm = encrypt(payload_v1())
msg = bytes([0x40]) + struct.pack("<I", devaddr) + bytes([0]) + struct.pack("<H", fcnt & 0xFFFF) + bytes([2]) + frm
b0 = bytes([0x49, 0, 0, 0, 0, 0]) + struct.pack("<I", devaddr) + struct.pack("<I", fcnt) + bytes([0, len(msg)])
c = cmac.CMAC(algorithms.AES(nwk)); c.update(b0 + msg)
phy = msg + c.finalize()[:4]

rxpk = {"tmst": int(time.time() * 1e6) & 0xFFFFFFFF, "freq": 868.1, "chan": 0, "rfch": 0, "stat": 1, "modu": "LORA",
        "datr": "SF9BW125", "codr": "4/5", "lsnr": 6.5, "rssi": -97, "size": len(phy), "data": base64.b64encode(phy).decode()}
pkt = bytes([2]) + struct.pack(">H", fcnt & 0xFFFF) + bytes([0]) + gw + json.dumps({"rxpk": [rxpk]}).encode()
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3)
s.sendto(pkt, (host, 1700))
try:
    print("PUSH_ACK:", s.recvfrom(64)[0][3] == 1)
except socket.timeout:
    print("keine PUSH_ACK")
print("gesendet: fcnt", fcnt, "devAddr", keys["devAddr"], len(phy), "Byte")
