#!/bin/sh
# Inside the container 127.0.0.1 is the container itself: point a local Supabase (127.0.0.1 / localhost in .env)
# at the host instead. Cloud URLs are left alone.
for var in SUPABASE_DB_URL SUPABASE_URL; do
  eval "val=\${$var:-}"
  [ -n "$val" ] && export "$var=$(printf '%s' "$val" | sed -E 's#(@|//)(127\.0\.0\.1|localhost)([:/])#\1host.docker.internal\3#')"
done
exec "$@"
