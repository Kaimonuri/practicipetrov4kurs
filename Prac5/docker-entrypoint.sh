#!/bin/sh
set -eu

# Новый Docker volume пустой, поэтому при первом запуске кладём в него исходную БД.
if [ ! -f "${DB_PATH}" ]; then
  cp /app/seed/dev.db "${DB_PATH}"
fi

exec "$@"
