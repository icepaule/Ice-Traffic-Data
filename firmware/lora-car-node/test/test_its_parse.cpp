#include <unity.h>
#include <vector>
#include "its_parse.h"

using Bytes = std::vector<uint8_t>;

static Bytes frame(uint16_t port, int basicNh = 1, int ht = 4) {
    Bytes f = {0x88, 0x00, 0x00, 0x00};
    f.insert(f.end(), 6, 0xFF);                                   // addr1
    f.insert(f.end(), {2, 0, 0, 0, 0, 1});                         // addr2
    f.insert(f.end(), 6, 0xFF);                                   // addr3
    f.insert(f.end(), {0, 0, 0, 0});                              // seq + QoS
    f.insert(f.end(), {0xAA, 0xAA, 3, 0, 0, 0, 0x89, 0x47});      // LLC
    f.insert(f.end(), {(uint8_t)(0x10 | basicNh), 0, 5, 1});  // Basic Header (Version 1, NH)
    f.insert(f.end(), {0x20, (uint8_t)(ht << 4), 0x50, 0x80, 0, 8, 1, 0});       // Common (BTP-B)
    f.insert(f.end(), (size_t)its::extLen(ht), 0);                // Extended
    f.push_back(port >> 8); f.push_back(port & 0xFF); f.push_back(0); f.push_back(0);  // BTP-B
    f.insert(f.end(), 8, 0x42);                                   // Nutzlast
    return f;
}

void test_classify_types() {
    TEST_ASSERT_EQUAL(its::K_CAM, its::classify(frame(2001).data(), frame(2001).size()));
    TEST_ASSERT_EQUAL(its::K_DENM, its::classify(frame(2002).data(), frame(2002).size()));
    TEST_ASSERT_EQUAL(its::K_MAPEM, its::classify(frame(2003).data(), frame(2003).size()));
    TEST_ASSERT_EQUAL(its::K_SPATEM, its::classify(frame(2004, 1, 3).data(), frame(2004, 1, 3).size()));
    TEST_ASSERT_EQUAL(its::K_OTHER, its::classify(frame(2999).data(), frame(2999).size()));
}

void test_secured_and_garbage() {
    Bytes s = frame(2001, 2);
    TEST_ASSERT_EQUAL(its::K_SECURED, its::classify(s.data(), s.size()));
    Bytes bad(20, 0);
    TEST_ASSERT_EQUAL(its::K_OTHER, its::classify(bad.data(), bad.size()));
    Bytes noLlc = frame(2001); noLlc[24 + 2 + 7] = 0;
    TEST_ASSERT_EQUAL(its::K_OTHER, its::classify(noLlc.data(), noLlc.size()));
}

void test_its5_stream() {
    Bytes fr = frame(2001);
    Bytes stream = {0x00, 'I', 'I', 'T', 'S', '5', 1, 0, 0, 0, 2, 0, 0, 0, (uint8_t)(fr.size() & 0xFF), (uint8_t)(fr.size() >> 8)};
    stream.insert(stream.end(), fr.begin(), fr.end());
    its::Its5Parser p; bool got = false;
    for (uint8_t b : stream) got = p.feed(b) || got;
    TEST_ASSERT_TRUE(got);
    TEST_ASSERT_EQUAL(fr.size(), p.size());
    TEST_ASSERT_EQUAL(its::K_CAM, its::classify(p.data(), p.size()));
}

void test_payload() {
    its::Counters c; for (int i = 0; i < 3; i++) c.add(its::K_CAM); c.add(its::K_SPATEM); c.add(its::K_SECURED);
    uint8_t o[its::PAYLOAD_LEN];
    size_t n = its::packPayload(o, c, its::F_GPS_FIX, 48123456, -11654321, 87, 9, 5);
    TEST_ASSERT_EQUAL(25, n);
    TEST_ASSERT_EQUAL(1, o[0]);
    TEST_ASSERT_EQUAL(48123456, (int32_t)((o[2] << 24) | (o[3] << 16) | (o[4] << 8) | o[5]));
    TEST_ASSERT_EQUAL(-11654321, (int32_t)((uint32_t)o[6] << 24 | o[7] << 16 | o[8] << 8 | o[9]));
    TEST_ASSERT_EQUAL(3, (o[12] << 8) | o[13]);
    TEST_ASSERT_EQUAL(1, (o[16] << 8) | o[17]);
    TEST_ASSERT_EQUAL(1, (o[20] << 8) | o[21]);
    TEST_ASSERT_EQUAL(5, o[24]);
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_classify_types);
    RUN_TEST(test_secured_and_garbage);
    RUN_TEST(test_its5_stream);
    RUN_TEST(test_payload);
    return UNITY_END();
}
