#!/usr/bin/env bash
# Erzeugt Passwoerter, ACL und installiert das Let's-Encrypt-Zertifikat fuer den oeffentlichen MQTT-Listener.
# Nutzung: ITS_DEPLOY=/opt/ice-traffic-data FQDN=its.mpauli.de ./scripts/setup-broker.sh
set -euo pipefail
D="${ITS_DEPLOY:?ITS_DEPLOY setzen}"; FQDN="${FQDN:?FQDN setzen}"
mkdir -p "$D/certs" "$D/secrets"; chmod 700 "$D/secrets"
# Zertifikat (acme.sh, bereits ausgestellt) installieren + bei Erneuerung Broker neu starten
~/.acme.sh/acme.sh --install-cert -d "$FQDN" --ecc \
  --fullchain-file "$D/certs/fullchain.pem" --key-file "$D/certs/privkey.pem" \
  --reloadcmd "chown -R 1883:1883 $D/certs; chmod 640 $D/certs/*; docker restart ice-traffic-data-mosquitto-1 2>/dev/null || true"
# Zugangsdaten nur anlegen, wenn noch nicht vorhanden
for u in car; do
  [ -f "$D/secrets/$u.pass" ] || { openssl rand -hex 16 > "$D/secrets/$u.pass"; chmod 600 "$D/secrets/$u.pass"; }
done
rm -f "$D/secrets/passwd"; touch "$D/secrets/passwd"
for u in car; do
  docker run --rm -v "$D/secrets:/s" eclipse-mosquitto:2 mosquitto_passwd -b /s/passwd "$u" "$(cat "$D/secrets/$u.pass")"
done
cat > "$D/secrets/acl" <<'ACL'
# Auto: nur schreiben, nichts lesen
user car
topic write its/+/packet
topic write its/+/status
topic write its/+/info
topic write its/+/stats
ACL
chown -R 1883:1883 "$D/secrets"; chmod 600 "$D/secrets/passwd" "$D/secrets/acl"; chmod 600 "$D/secrets/"*.pass
echo "fertig. Passwort des Users 'car': $D/secrets/car.pass"
