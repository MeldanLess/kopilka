#!/usr/bin/env bash
#
# Ночная резервная копия PostgreSQL «Копилки».
#
# Запускается systemd-таймером из этого каталога. Снимает сжатый дамп,
# хранит последние KEEP_N дампов.
#
#   sudo ./deploy/backup.sh
#
# Восстановление:
#   gunzip -c /opt/kopilka/backups/kopilka-20261117-030000.sql.gz \
#     | docker compose -f docker-compose.prod.yml exec -T db psql -U kopilka kopilka

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/kopilka/backups}"
KEEP_N="${KEEP_N:-14}"                      # две недели ночных дампов
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
PROJECT_DIR="${PROJECT_DIR:-/opt/kopilka}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
FILENAME="kopilka-${TIMESTAMP}.sql.gz"

# Каталог закрыт от всех, кроме владельца: дамп содержит почты пользователей
# и хеши паролей, а каталог по умолчанию создаётся с правами 755.
install -d -m 700 "$BACKUP_DIR"

cd "$PROJECT_DIR"

echo "Снимаем резервную копию базы в ${BACKUP_DIR}/${FILENAME}"

docker compose -f "$COMPOSE_FILE" exec -T db \
    sh -c 'pg_dump --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip -9 > "${BACKUP_DIR}/${FILENAME}"

# Пустой дамп хуже, чем никакого дампа: он выглядит как успешный.
if [ ! -s "${BACKUP_DIR}/${FILENAME}" ]; then
    echo "ОШИБКА: резервная копия пустая" >&2
    exit 1
fi

gzip -t "${BACKUP_DIR}/${FILENAME}" || {
    echo "ОШИБКА: резервная копия повреждена" >&2
    exit 1
}

# Файл с дампом — тоже только для владельца.
chmod 600 "${BACKUP_DIR}/${FILENAME}"

# Удаляем самые старые дампы, оставляя KEEP_N самых свежих.
ls -1t "${BACKUP_DIR}"/kopilka-*.sql.gz 2>/dev/null \
  | tail -n "+$((KEEP_N + 1))" \
  | xargs -r rm --

echo "Готово. На диске: $(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)."
