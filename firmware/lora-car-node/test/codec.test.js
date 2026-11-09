// Prueft, dass der JS-Codec dieselbe Nutzlast liest, die its_parse.h packt (Werte wie in test_payload).
const { decodeUplink } = require('../chirpstack-codec.js');
const assert = require('assert');
const b = Buffer.alloc(25);
b[0] = 1; b[1] = 1; b.writeInt32BE(48123456, 2); b.writeInt32BE(-11654321, 6);
b[10] = 87; b[11] = 9; b.writeUInt16BE(3, 12); b.writeUInt16BE(1, 16); b.writeUInt16BE(1, 20); b[24] = 5;
const r = decodeUplink({ bytes: [...b] });
assert.ok(!r.errors, JSON.stringify(r));
assert.strictEqual(r.data.latitude, 48.123456);
assert.strictEqual(r.data.longitude, -11.654321);
assert.strictEqual(r.data.cam, 3); assert.strictEqual(r.data.spatem, 1); assert.strictEqual(r.data.secured, 1);
assert.strictEqual(r.data.speed_kmh, 87); assert.strictEqual(r.data.uptime_min, 50);
assert.ok(decodeUplink({ bytes: [1, 2] }).errors);
b[1] = 0; assert.strictEqual(decodeUplink({ bytes: [...b] }).data.latitude, null);
// v2: Funkstrecke
const v2 = Buffer.alloc(36); b.copy(v2); v2[0] = 2; v2[1] = 1;
v2[25] = 0xc3; v2[26] = 0xb0; v2[27] = 0xd8; v2.writeUInt16BE(258, 28); v2.writeUInt16BE(2, 30); v2.writeUInt16BE(65535, 32); v2.writeUInt16BE(1, 34);
const r2 = decodeUplink({ bytes: [...v2] }).data;
assert.strictEqual(r2.version, 2); assert.strictEqual(r2.cam, 3);
assert.strictEqual(r2.sniffer_rssi_avg, -61); assert.strictEqual(r2.sniffer_rssi_min, -80); assert.strictEqual(r2.sniffer_rssi_max, -40);
assert.strictEqual(r2.sniffer_rx_err, 258); assert.strictEqual(r2.sniffer_unicast, 2); assert.strictEqual(r2.sniffer_dropped, 65535); assert.strictEqual(r2.frames_lost, 1);
v2[25] = 127; assert.strictEqual(decodeUplink({ bytes: [...v2] }).data.sniffer_rssi_avg, null);
assert.ok(decodeUplink({ bytes: [...b].map((x, i) => i === 0 ? 2 : x) }).errors);  // v2 mit 25 Byte
console.log('codec ok');
