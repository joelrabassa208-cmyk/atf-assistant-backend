# Actualización del backend ATF Assistant en Render

El servidor actualmente publicado corresponde a la versión 1.0 y no contiene
las rutas de vehículos. Esta carpeta contiene la versión 1.1.

## Archivos que deben quedar en el repositorio del backend

- `main.py`
- `database.py`
- `atf_assistant.db`
- `requirements.txt`

No copies ni subas el archivo `.env`. La clave `OPENAI_API_KEY` debe permanecer
en **Render > Environment**.

## Configuración de Render

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/`

## Resultado esperado

Después de publicar, estas direcciones deben responder:

- `/` — versión `1.1.0`
- `/api/vehicles` — lista de vehículos
- `/api/vehicles/1` — ficha del vehículo 1
- `/atf-assistant` — asistente IA

La base incluida contiene 38 variantes de vehículos. Solo dos relaciones de
transmisión poseen actualmente datos de fluido; los demás registros deben
seguir apareciendo como pendientes de validación.
