# ATF Assistant Backend 2.0 — Etapa 1 SaaS: base sólida

Mismas rutas que la 1.6 (la app Flutter no necesita cambios). Lo que cambia
es la estructura interna y la base de datos.

## Estructura

```
main.py                  # entrada para Render: `uvicorn main:app`
app/
  main.py                # crea la app, migra e importa al arrancar
  config.py              # todas las variables de entorno
  security.py            # claves ATF_API_KEY / ATF_ADMIN_KEY
  db/database.py         # conexión (SQLite o Postgres) y transacciones
  catalog/               # vehículos, catálogo ATF, revisión, estadísticas
  assistant/             # asistente IA
  importers/             # planillas de data/ -> base, con la vinculación
migrations/              # Alembic (versiones del esquema)
scripts/
  sqlite_to_postgres.py  # copia única de los datos actuales a Postgres
  legacy/                # seeds v1.3/v1.4, solo para el SQLite viejo
tests/
```

## Base de datos

- Sin `DATABASE_URL` usa `atf_assistant.db` (igual que antes).
- Con `DATABASE_URL` usa Postgres. Acepta el formato `postgres://...` que da Render.
- El esquema lo maneja Alembic. Al arrancar se ejecuta `alembic upgrade head`
  (desactivable con `RUN_MIGRATIONS=false`). La migración inicial adopta la
  base SQLite existente sin perder datos.

## Pasar Render a Postgres (una vez)

1. En Render: **New > PostgreSQL** (región igual al servicio web).
2. En la PC, con el repo actualizado:
   ```powershell
   pip install -r requirements.txt
   $env:DATABASE_URL="<External Database URL de Render>"
   alembic upgrade head
   python scripts/sqlite_to_postgres.py
   ```
3. En el servicio web, **Environment**: agregar `DATABASE_URL` con la
   *Internal Database URL*. Guardar y redeployar.
4. Verificar `/` (`database: connected`), `/api/atf-stats` y la app.

Desde ese momento las revisiones manuales y cualquier dato nuevo persisten
entre deploys. `atf_assistant.db` queda solo para desarrollo local.

## Tests

```powershell
python -m unittest discover tests
```

## Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `DATABASE_URL` | SQLite local | Postgres en producción |
| `RUN_MIGRATIONS` | `true` | Migrar al arrancar |
| `IMPORT_ON_STARTUP` | `true` | Reimportar planillas de `data/` al arrancar |
| `OPENAI_API_KEY` | — | Asistente IA |
| `OPENAI_MODEL` | `gpt-5.6-luna` | Modelo del asistente |
| `ATF_API_KEY` | — | Si está, `/atf-assistant` exige `X-API-Key` |
| `ATF_ADMIN_KEY` | — | Habilita la revisión manual (`X-Admin-Key`) |
| `ALLOWED_ORIGINS` | — | CORS para un frontend web |
