# Runbook basico de incidentes

## 1) DB caida
- Sintoma: fallan pantallas con errores de conexion.
- Accion:
  1. Revisar estado en Render.
  2. Validar `DATABASE_URL` en Streamlit.
  3. Reintentar conexion y revisar logs.
- Mitigacion: activar backup semanal y export manual adicional previo a cambios grandes.

## 2) Error de ingesta CSV
- Sintoma: alta tasa de errores por fila o import parcial.
- Accion:
  1. Descargar errores por fila desde UI.
  2. Verificar delimitador/encoding detectado.
  3. Ajustar formato fecha en UI y reintentar.
- Mitigacion: fixtures de pruebas por banco/fuente.

## 3) Regresion de sugerencias
- Sintoma: categorias sugeridas incorrectas de forma sistematica.
- Accion:
  1. Validar precision por `source` (`map_exact`, `history`, `similarity`).
  2. Bajar umbral de auto-sugerencia solo si hay evidencia.
  3. Reentrenar `categoria_map` via flujo manual.

## 4) Rollback
- Condicion: bug critico en produccion.
- Accion:
  1. Revertir release en GitHub.
  2. Ejecutar downgrade de migracion si corresponde.
  3. Restaurar backup si hubo corrupcion.
