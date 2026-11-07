# ATF Assistant Backend 1.6

## Corrección importante: vinculación taller ↔ referencia

En la v1.5, 16 de los 25 registros marcados `WORKSHOP_CONFIRMED` estaban
vinculados a un vehículo del taller con otra caja o motor (por ejemplo
Jeep Compass 2.0 ZF 9HP con "JEEP COMPASS 2.4 - CAJA AT6"). La causa era que
la comparación buscaba substrings: el "2" de "2.0" coincidía con cualquier
"2" del texto, y no se controlaban contradicciones.

Ahora la vinculación:

- compara palabras completas de marca y modelo;
- descarta pares con distinta cilindrada, tipo de caja (AT / CVT / doble
  embrague), cantidad de marchas o fabricante de caja (ZF, Aisin, Jatco...);
- no toma "C4" para un registro "C4 LOUNGE" si ese modelo existe aparte;
- exige modelo + cilindrada + un dato de caja para confianza `ALTA`.

Resultado con los datos actuales: 14 confirmados (antes 25, con 16 erróneos).
Tests en `tests/test_matching.py` (`python -m unittest discover tests`).

## Novedades

- `PATCH /api/atf-catalog/{id}/review` — revisión manual
  (`WORKSHOP_CONFIRMED`, `PENDING_REVIEW` o `REJECTED`). Requiere header
  `X-Admin-Key` igual a `ATF_ADMIN_KEY`. Sin esa variable, queda deshabilitado.
  Las revisiones manuales ya no se pisan al reimportar en cada arranque.
- `POST /atf-assistant` acepta `catalog_id` y/o `vehicle_id` opcionales: el
  asistente recibe los datos de la base de ese vehículo y su estado de validación.
- Las filas borradas de las planillas se eliminan de la base al importar.
- Errores de OpenAI ya no se devuelven al cliente (quedan en el log).

## Variables de entorno nuevas (todas opcionales)

| Variable | Uso |
|---|---|
| `ATF_API_KEY` | Si está, `/atf-assistant` exige header `X-API-Key`. |
| `ATF_ADMIN_KEY` | Habilita el endpoint de revisión (header `X-Admin-Key`). |
| `ALLOWED_ORIGINS` | Orígenes CORS separados por coma, para un frontend en otro dominio. |
| `OPENAI_MODEL` | Modelo del asistente (por defecto `gpt-5.6-luna`). |

## Atención en Render

El disco de Render es efímero: lo que se escribe en `atf_assistant.db`
(incluidas revisiones manuales) se pierde en cada deploy. Para conservarlas
hace falta un disco persistente o pasar a Postgres (ver propuesta SaaS).
