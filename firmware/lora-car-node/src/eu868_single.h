#pragma once
// Einkanal-Variante des EU868-Bandplans (nur 868,1 MHz, nur DR3 = SF9/125 kHz) fuer das Heim-Einkanal-Gateway.
// Uebernommen 1:1 aus dem IceGeigerCounter-Projekt (dort mit ChirpStack validiert); Original: RadioLib LoRaWANBands.cpp.
#include <RadioLib.h>
const LoRaWANBand_t EU868_SINGLE = {
  .bandNum = BandEU868,
  .bandType = RADIOLIB_LORAWAN_BAND_DYNAMIC,
  .freqMin = 8630000,
  .freqMax = 8700000,
  .payloadLenMax = {  51,  51,  51, 115, 242, 242, 242, 242,  50, 115,  50, 115,   0,   0,   0 },
  .powerMax = 16,
  .powerNumSteps = 7,
  .dutyCycle = 36000,
  .dwellTimeUp = 0,
  .dwellTimeDn = 0,
  .txParamSupported = false,
  .txFreqs = {
    { .idx = 0, .freq = 8681000, .drMin = 3, .drMax = 3, .dr = 3 },
    RADIOLIB_LORAWAN_CHANNEL_NONE,
    RADIOLIB_LORAWAN_CHANNEL_NONE,
  },
  .numTxSpans = 0,
  .txSpans = {
    RADIOLIB_LORAWAN_CHANNEL_SPAN_NONE,
    RADIOLIB_LORAWAN_CHANNEL_SPAN_NONE
  },
  .rx1Span = RADIOLIB_LORAWAN_CHANNEL_SPAN_NONE,
  .rx1DrTable = {
    {    0,    0,    0,    0,    0,    0, 0x0F, 0x0F },
    {    1,    0,    0,    0,    0,    0, 0x0F, 0x0F },
    {    2,    1,    0,    0,    0,    0, 0x0F, 0x0F },
    {    3,    2,    1,    0,    0,    0, 0x0F, 0x0F },
    {    4,    3,    2,    1,    0,    0, 0x0F, 0x0F },
    {    5,    4,    3,    2,    1,    0, 0x0F, 0x0F },
    {    6,    5,    4,    3,    2,    1, 0x0F, 0x0F },
    {    7,    6,    5,    4,    3,    2, 0x0F, 0x0F },
    {    1,    0,    0,    0,    0,    0, 0x0F, 0x0F },
    {    2,    1,    0,    0,    0,    0, 0x0F, 0x0F },
    {    1,    0,    0,    0,    0,    0, 0x0F, 0x0F },
    {    2,    1,    0,    0,    0,    0, 0x0F, 0x0F },
    { 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F },
    { 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F },
    { 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F }
  },
  .rx2 = { .idx = 0, .freq = 8695250, .drMin = 0, .drMax = 7, .dr = 0 },
  .txWoR = {
    { .idx = 0, .freq = 8651000, .drMin = 3, .drMax = 3, .dr = 3 },
    { .idx = 1, .freq = 8655000, .drMin = 3, .drMax = 3, .dr = 3 }
  },
  .txAck = {
    { .idx = 0, .freq = 8653000, .drMin = 3, .drMax = 3, .dr = 3 },
    { .idx = 1, .freq = 8659000, .drMin = 3, .drMax = 3, .dr = 3 }
  },
  .dataRates = {
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = {12, 125, 5}}, .pc = {.lora = {8, false, true, true}}},
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = {11, 125, 5}}, .pc = {.lora = {8, false, true, true}}},
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = {10, 125, 5}}, .pc = {.lora = {8, false, true, false}}},
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = { 9, 125, 5}}, .pc = {.lora = {8, false, true, false}}},
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = { 8, 125, 5}}, .pc = {.lora = {8, false, true, false}}},
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = { 7, 125, 5}}, .pc = {.lora = {8, false, true, false}}},
    { .modem = RADIOLIB_MODEM_LORA,   .dr = {.lora = { 7, 250, 5}}, .pc = {.lora = {8, false, true, false}}},
    { .modem = RADIOLIB_MODEM_FSK,    .dr = {.fsk  = {50, 25}},     .pc = {.fsk  = {40, 24, 2}}},
    { .modem = RADIOLIB_MODEM_LRFHSS, .dr = {.lrFhss = {2, 3, 1}},  .pc = {.lrFhss = {3}}},
    { .modem = RADIOLIB_MODEM_LRFHSS, .dr = {.lrFhss = {2, 1, 1}},  .pc = {.lrFhss = {2}}},
    { .modem = RADIOLIB_MODEM_LRFHSS, .dr = {.lrFhss = {4, 3, 1}},  .pc = {.lrFhss = {3}}},
    { .modem = RADIOLIB_MODEM_LRFHSS, .dr = {.lrFhss = {4, 1, 1}},  .pc = {.lrFhss = {2}}},
    RADIOLIB_DATARATE_NONE,
    RADIOLIB_DATARATE_NONE,
    RADIOLIB_DATARATE_NONE
  }
};
