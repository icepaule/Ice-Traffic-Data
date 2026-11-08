#pragma once
// Nach secrets.h kopieren, lokal fuellen, NIE committen (steht in .gitignore).
// Werte stammen aus ChirpStack (Geraet "ice-car"), siehe scripts/provision-chirpstack.py
#define CAR_SECRETS_CONFIGURED 0
static const uint32_t CAR_DEV_ADDR = 0;
static const uint8_t CAR_NWK_S_KEY[16] = {0};
static const uint8_t CAR_APP_S_KEY[16] = {0};
// Eigenes WLAN des Auto-Knotens (Statusseite http://192.168.4.1), Passwort mind. 8 Zeichen
static const char CAR_AP_SSID[] = "IceCar";
static const char CAR_AP_PASS[] = "AENDERN-mind8";
