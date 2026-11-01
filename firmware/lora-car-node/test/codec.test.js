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
console.log('codec ok');
