#!/bin/bash
set -e

APP_NAME="veldriklabs-whatsapp-bot"
IMAGE_NAME="veldriklabs-whatsapp-bot"
TEST_NAME="veldriklabs-whatsapp-bot-test"
TEST_PORT="5101"

echo "== VeldrikLabs Safe Deploy =="

echo "1) Verificando archivos..."
test -f app.py
test -f Dockerfile
test -f requirements.txt

echo "2) Verificando sintaxis Python..."
python3 -m py_compile app.py

echo "3) Construyendo imagen nueva..."
docker build -t ${IMAGE_NAME}:new .

echo "4) Eliminando contenedor temporal anterior si existe..."
docker rm -f ${TEST_NAME} >/dev/null 2>&1 || true

echo "5) Levantando contenedor temporal..."
docker run -d \
  --name ${TEST_NAME} \
  --network gamehosting-observability-lab_default \
  --env-file .env \
  -p ${TEST_PORT}:5100 \
  ${IMAGE_NAME}:new

echo "6) Esperando health check..."
sleep 5

curl -fsS http://127.0.0.1:${TEST_PORT}/health >/dev/null

echo "7) Health OK. Probando dashboard..."
curl -fsS -I http://127.0.0.1:${TEST_PORT}/whatsapp/dashboard >/dev/null
curl -fsS -I http://127.0.0.1:${TEST_PORT}/whatsapp/dashboard/agenda >/dev/null
curl -fsS -I http://127.0.0.1:${TEST_PORT}/whatsapp/dashboard/services >/dev/null

echo "8) Marcando versión anterior..."
docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:previous >/dev/null 2>&1 || true

echo "9) Deteniendo producción actual..."
docker rm -f ${APP_NAME} >/dev/null 2>&1 || true

echo "10) Publicando nueva versión..."
docker tag ${IMAGE_NAME}:new ${IMAGE_NAME}:latest

docker run -d \
  --name ${APP_NAME} \
  --network gamehosting-observability-lab_default \
  --env-file .env \
  --restart unless-stopped \
  -p 5100:5100 \
  ${IMAGE_NAME}:latest

echo "11) Probando producción..."
sleep 5
curl -fsS http://127.0.0.1:5100/health >/dev/null

echo "12) Limpiando contenedor temporal..."
docker rm -f ${TEST_NAME} >/dev/null 2>&1 || true

echo "DEPLOY EXITOSO"
