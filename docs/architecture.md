# Arquitectura Los Factos v2

## Principios
- UI separada de negocio y persistencia.
- Operaciones no destructivas por defecto.
- Confiabilidad de datos primero: dedup, tombstones, trazabilidad.
- Configuracion por variables de entorno.

## Capas
- `app.py`: router y manejo de errores UI.
- `ui/`: vistas Streamlit y componentes visuales.
- `services/`: casos de uso de negocio.
- `data/`: modelos, repositorios y queries SQL parametrizadas.
- `charts/`: construccion de graficos.
- `utils/`: normalizacion, hashing, formato, config, logging.

## Persistencia
Tablas base:
- `movimientos`
- `categorias`
- `categoria_map`
- `movimientos_borrados`
- `movimientos_ignorados`

Indices obligatorios:
- `unique_key`
- `fecha`
- `categoria`
- `detalle_norm`

## Convencion de montos
- DB: `monto_abs_clp` siempre positivo.
- Tipo: `tipo_movimiento` (`GASTO`, `INGRESO`, `NEUTRO`).
- UI: gasto se muestra negativo para lectura humana.

## Rollback
- Migraciones reversibles con Alembic.
- `downgrade` soportado en cada revision.
