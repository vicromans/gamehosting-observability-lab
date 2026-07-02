#!/bin/bash

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR" || exit 1

APP_NAME="veldriklabs-whatsapp-bot"
DB_NAME="gamehosting-db"

status_line() {
  local label="$1"
  local command="$2"

  if eval "$command" >/dev/null 2>&1; then
    printf "%-22s %s\n" "$label" "OK"
  else
    printf "%-22s %s\n" "$label" "FAIL"
  fi
}

show_header() {
  clear
  echo "========================================="
  echo "      VeldrikLabs Operations Center"
  echo "========================================="
  echo
  echo "Sistema: Aura Beauty / WhatsApp Bot"
  echo

  echo "Estado general:"
  status_line "Bot container:" "docker ps --format '{{.Names}}' | grep -qx '$APP_NAME'"
  status_line "Health endpoint:" "curl -fsS http://127.0.0.1:5100/health"
  status_line "Dashboard:" "curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard | grep -q '200 OK'"
  status_line "Agenda:" "curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard/agenda | grep -q '200 OK'"
  status_line "Servicios:" "curl -fsS -I http://127.0.0.1:5100/whatsapp/dashboard/services | grep -q '200 OK'"
  status_line "MariaDB:" "docker exec $DB_NAME sh -c 'mariadb -u\"\$MARIADB_USER\" -p\"\$MARIADB_PASSWORD\" \"\$MARIADB_DATABASE\" -e \"SELECT 1;\"'"
  status_line "Docker network:" "docker inspect $APP_NAME --format '{{json .NetworkSettings.Networks}}' | grep -q gamehosting-observability-lab_default"

  echo
  echo "Servidor:"
  echo "Disco:     $(df -h / | awk 'NR==2 {print $5 " usado de " $2}')"
  echo "Memoria:   $(free -h | awk '/Mem:/ {print $3 " usado de " $2}')"
  echo "Uptime:    $(uptime -p)"
  echo

  echo "Git:"
  echo "Branch:    $(git branch --show-current)"
  echo "Commit:    $(git log -1 --oneline)"
  if [ -n "$(git status --porcelain)" ]; then
    echo "Estado:    Cambios pendientes"
  else
    echo "Estado:    Limpio"
  fi

  echo
  echo "Contenedores activos:"
  docker ps --format "{{.Names}}" | wc -l | awk '{print "Total:     " $1}'
  echo
  echo "========================================="
}

while true; do
  show_header
  echo
  echo "1) Health Check completo"
  echo "2) Safe Deploy"
  echo "3) Rollback"
  echo "4) Ver Logs del Bot"
  echo "5) Estado de Contenedores"
  echo "6) Git Status"
  echo "7) Últimos errores del Bot"
  echo "8) Salir"
  echo
  read -p "Seleccione una opción: " option

  echo

  case "$option" in
    1)
      ./scripts/health-check.sh
      ;;
    2)
      ./scripts/deploy-safe.sh
      ;;
    3)
      ./scripts/rollback-whatsapp.sh
      ;;
    4)
      docker logs --tail=100 $APP_NAME
      ;;
    5)
      docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
      ;;
    6)
      git status
      echo
      echo "Último commit:"
      git log -1 --oneline
      ;;
    7)
      docker logs --tail=300 $APP_NAME 2>&1 | grep -i "error\|exception\|traceback" | tail -60 || echo "Sin errores recientes"
      ;;
    8)
      echo "Saliendo..."
      exit 0
      ;;
    *)
      echo "Opción inválida"
      ;;
  esac

  echo
  read -p "Presione ENTER para continuar..."
done
