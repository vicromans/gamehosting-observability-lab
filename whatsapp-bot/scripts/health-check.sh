#!/bin/bash
set -e

echo "== VeldrikLabs WhatsApp Health Check =="

echo "1) Contenedor bot:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep veldriklabs-whatsapp-bot

echo "2) Health endpoint:"
curl -fsS http://127.0.0.1:5100/health

echo
echo "3) Dashboard principal:"
curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard | head -1

echo "4) Agenda:"
curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard/agenda | head -1

echo "5) Servicios:"
curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard/services | head -1

echo "6) Base de datos:"
docker exec gamehosting-db sh -c 'mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" -e "SELECT 1;"' >/dev/null
echo "MariaDB OK"

echo "7) Red Docker:"
docker inspect veldriklabs-whatsapp-bot --format '{{json .NetworkSettings.Networks}}' | grep gamehosting-observability-lab_default >/dev/null
echo "Network OK"

echo "HEALTH CHECK OK"
