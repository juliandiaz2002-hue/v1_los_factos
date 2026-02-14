# Los Factos v2

Aplicacion de gastos personales en Streamlit con PostgreSQL (Render), arquitectura modular y foco en confiabilidad de datos.

## Stack
- Python 3.11
- Streamlit
- PostgreSQL
- SQLAlchemy + Alembic

## Estructura
- `app.py`: orquestacion de paginas
- `ui/`: interfaz y componentes
- `services/`: logica de negocio
- `data/`: persistencia, repositorios y queries
- `charts/`: constructores de visualizaciones
- `utils/`: normalizacion, formato, hashing, config
- `tests/`: unit e integracion

## Setup local
1. Crear entorno:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Configurar variables:
```bash
cp .env.example .env
```
3. Ejecutar migraciones:
```bash
alembic upgrade head
```
4. Correr app:
```bash
streamlit run app.py
```

## Deploy
- Produccion: branch `main` en Streamlit Community Cloud
- Staging: branch `develop` en Streamlit Community Cloud (app separada)

## Seguridad
- Nunca commitear secretos.
- Todas las conexiones salen de `DATABASE_URL` por variables de entorno.
