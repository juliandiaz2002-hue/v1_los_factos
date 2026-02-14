# Deploy: Render PostgreSQL + Streamlit Community Cloud

## 1. PostgreSQL en Render
1. Crear instancia PostgreSQL en Render.
2. Copiar `External Database URL`.
3. Guardar como `DATABASE_URL` en Streamlit Cloud.

## 2. GitHub
- `main`: produccion estable.
- `develop`: integracion y staging.
- `codex/feature-*`: trabajo incremental.

## 3. Staging y Produccion
- Crear app Streamlit A (staging) conectada a branch `develop`.
- Crear app Streamlit B (produccion) conectada a branch `main`.
- Ambas usan la misma imagen de runtime Python 3.11.

## 4. Secrets en Streamlit Cloud
- `DATABASE_URL`
- `APP_ENV` (`staging` o `production`)
- `LOG_LEVEL`
- `DEFAULT_DATE_FORMATS`
- `DEFAULT_TIMEZONE`

## 5. Migraciones
En pipeline o manual:
```bash
alembic upgrade head
```
Antes de rollback:
```bash
alembic downgrade -1
```
