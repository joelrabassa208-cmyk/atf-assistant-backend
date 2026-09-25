# ATF Assistant Backend 1.5

Esta versión incorpora la base consolidada creada con dos fuentes:

- Registro real del taller: 166 filas válidas. La fila vacía se descarta.
- Referencia técnica complementaria: 181 registros.

## Nuevos endpoints

- `GET /api/atf-stats`
- `GET /api/atf-catalog`
- `GET /api/atf-catalog?brand=Chevrolet&model=Spin`
- `GET /api/atf-catalog?pending_only=true`
- `GET /api/atf-catalog/{id}`

La respuesta individual diferencia `workshop_liters` de `reference_liters`.
`recommended_service_liters` prioriza el dato real del taller cuando existe.

Los registros con `PENDING_REVIEW` no deben habilitar automáticamente un
procedimiento definitivo. Hay que confirmar el código físico de transmisión,
la especificación OEM y el método de control de nivel.

## Render

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Al iniciar, el backend crea las tablas e importa las dos planillas. La
importación es idempotente: puede ejecutarse nuevamente sin duplicar filas.
