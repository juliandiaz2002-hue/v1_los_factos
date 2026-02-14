# Staging Checklist v2

Checklist operativo previo a merge a `main` y deploy en Streamlit Community Cloud.

## 1) Configuracion minima
- `APP_ENV=staging`
- `DATABASE_URL` apuntando a Postgres de staging (no produccion).
- `LOG_LEVEL=INFO` (o `DEBUG` temporal para investigacion).
- Migraciones aplicadas:
  ```bash
  alembic upgrade head
  ```

## 2) Smoke test funcional (bloqueante)
- Ingesta CSV:
  - Deteccion de encoding (`utf-8`, `latin-1`, `cp1252`).
  - Deteccion de delimitador.
  - Alias de columnas (`glosa/descripcion/concepto`, `cargo/importe/debe`, etc).
  - Fechas `%Y-%m-%d` y `%Y-%d-%m`.
- Dedupe/tombstones:
  - Reimport de archivo no duplica.
  - Movimiento eliminado no revive al reimportar.
- Sugerencias:
  - Aceptar sugerencia categoriza y saca fila de pendientes.
  - Rechazar + categorizacion manual guarda categoria y aprende en sugerencias futuras.
- Movimientos:
  - Edicion masiva funciona.
  - Eliminacion individual funciona.
  - Export CSV enriquecido funciona.
- Backup y confiabilidad:
  - Export completo DB funciona.
  - Diagnostico de base no reporta inconsistencias criticas.

## 3) Proyecciones (nueva version)
- Escenario 90 dias incluye:
  - Mes anterior real.
  - Mes actual real/proyectado.
  - 3 meses siguientes proyectados.
- Modo de sensibilidad disponible en UI:
  - `Conservador`, `Balanceado`, `Agresivo`.
- La metodologia explica:
  - Umbrales de recurrencia calibrados.
  - Penalizacion de categorias esporadicas de ticket alto.

## 4) Insights (nueva version)
- 3 insights core siempre visibles:
  - Ritmo al dia.
  - Riesgo de cierre.
  - Concentracion por categoria.
- 2 insights dinamicos por contexto:
  - Seleccionados por prioridad segun comportamiento del mes.
- Tooltip funcional en cada insight (hover/focus) con formula/explicacion.

## 5) Criterios de salida a produccion
- Sin errores bloqueantes en ingesta/sugerencias/edicion/backup.
- Dashboard carga sin errores con datos reales de Postgres.
- Comparaciones mensuales usan corte al dia actual.
- Registro de cambios documentado en PR con:
  - impacto funcional,
  - pruebas ejecutadas,
  - screenshots de dashboard.

## 6) Flujo Git recomendado
1. Branch de trabajo: `codex/feature-*`.
2. PR a `develop` (staging).
3. Validacion en app de staging.
4. PR de `develop` a `main` solo con checklist completo.
