# ATF Assistant Backend 1.4

Primer lote técnico por marcas: Chevrolet, Ford y Toyota.

## Datos oficiales incorporados

- Chevrolet Onix 2025: DEXRON VI.
- Chevrolet Spin 2025: DEXRON VI; uso severo, cambio cada 80.000 km.
- Chevrolet S10 2025: DEXRON HP; cambio indicado cada 70.000 km.
- Ford Ranger 6R80 2012-2022: MERCON LV, Ford WSS-M2C938-A;
  capacidad seca de referencia 10,5 L.
- Ford Fiesta, Focus y EcoSport DPS6: Motorcraft XT-11-QDC,
  Ford WSS-M2C200-D2. No realizar diálisis como caja automática convencional.
- Toyota Hilux 2023 automática: Toyota Genuine ATF WS;
  volumen total de referencia 9,5 L.

Las capacidades totales no son cantidades de drenaje ni reposición. Los campos
de cantidad de servicio y método de nivel permanecen vacíos cuando la fuente
oficial revisada no los documenta claramente.

## Despliegue

Reemplazar los archivos del repositorio y ejecutar:

```powershell
git add main.py database.py atf_assistant.db requirements.txt seed_verified_cft_v14.py README_V1_4.md
git commit -m "ATF Assistant 1.4: datos Chevrolet Ford Toyota"
git push origin main
```

Render desplegará automáticamente. La ruta `/api/vehicles` debe informar
`count: 109`.
