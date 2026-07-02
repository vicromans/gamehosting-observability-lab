#!/bin/bash
set -e

APP_NAME="veldriklabs-whatsapp-bot"
IMAGE_NAME="veldriklabs-whatsapp-bot"

echo "== VeldrikLabs Rollback =="

docker image inspect ${IMAGE_NAME}:previous >/dev/null

docker rm -f ${APP_NAME} >/dev/null 2>&1 || true

docker run -d \
  --name ${APP_NAME} \
  --network gamehosting-observability-lab_default \
  --env-file .env \
  --restart unless-stopped \
  -p 5100:5100 \
  ${IMAGE_NAME}:previous

sleep 5

curl -fsS http://127.0.0.1:5100/health >/dev/null
curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard >/dev/null

echo "ROLLBACK EXITOSO"
