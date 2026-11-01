#pragma once
// Nach secrets.h kopieren, lokal fuellen, NIE committen (steht in .gitignore).
// Werte stammen aus ChirpStack (Geraet "ice-car"), siehe scripts/provision-chirpstack.py
#define CAR_SECRETS_CONFIGURED 0
static const uint32_t CAR_DEV_ADDR = 0;
static const uint8_t CAR_NWK_S_KEY[16] = {0};
static const uint8_t CAR_APP_S_KEY[16] = {0};
