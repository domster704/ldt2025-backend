#!/bin/sh
set -eu

read_secret() { cat "/run/secrets/$1"; }

APP_MIGRATOR_PASSWORD="$(read_secret app_migrator_password)"
APP_RUNTIME_PASSWORD="$(read_secret app_runtime_password)"
APP_READONLY_PASSWORD="$(read_secret app_readonly_password)"
KEYCLOAK_PASSWORD="$(read_secret keycloak_db_password)"

: "${POSTGRES_USER:=postgres}"
: "${POSTGRES_DB:=postgres}"
: "${POSTGRES_PASSWORD:=}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -v db="${POSTGRES_DB}" \
  -v app_migrator_password="${APP_MIGRATOR_PASSWORD}" \
  -v app_runtime_password="${APP_RUNTIME_PASSWORD}" \
  -v app_readonly_password="${APP_READONLY_PASSWORD}" \
  -v keycloak_password="${KEYCLOAK_PASSWORD}" <<'SQL'
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS kc_auth;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_migrator') THEN
    CREATE ROLE app_migrator LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
    CREATE ROLE app_runtime LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly') THEN
    CREATE ROLE app_readonly LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'keycloak') THEN
    CREATE ROLE keycloak LOGIN;
  END IF;
END
$$ LANGUAGE plpgsql;

ALTER ROLE app_migrator LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB CONNECTION LIMIT -1 PASSWORD :'app_migrator_password';
ALTER ROLE app_runtime  LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB CONNECTION LIMIT -1 PASSWORD :'app_runtime_password';
ALTER ROLE app_readonly LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB CONNECTION LIMIT -1 PASSWORD :'app_readonly_password';
ALTER ROLE keycloak     LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB CONNECTION LIMIT -1 PASSWORD :'keycloak_password';

REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO app_migrator, app_runtime, app_readonly, keycloak;

GRANT USAGE ON SCHEMA crm TO app_migrator, app_runtime, app_readonly;
GRANT CREATE ON SCHEMA crm TO app_migrator;

GRANT USAGE, CREATE ON SCHEMA kc_auth TO keycloak;
ALTER SCHEMA kc_auth OWNER TO keycloak;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA crm TO app_runtime;
GRANT SELECT ON ALL TABLES IN SCHEMA crm TO app_readonly;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA crm TO app_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA crm TO app_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA crm
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA crm
  GRANT SELECT ON TABLES TO app_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA crm
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA crm
  GRANT USAGE, SELECT ON SEQUENCES TO app_readonly;
SQL