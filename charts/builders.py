"""Funciones puras para construir graficos."""

from __future__ import annotations

import pandas as pd
import plotly.express as px

PALETTE = [
    "#6366F1",
    "#8B5CF6",
    "#EC4899",
    "#F59E0B",
    "#10B981",
    "#06B6D4",
    "#F43F5E",
    "#84CC16",
]


def _empty_chart(message: str):
    return px.scatter(title=message)


def category_distribution_chart(df: pd.DataFrame):
    if df.empty:
        return _empty_chart("Sin datos para distribucion")

    grouped = (
        df.groupby("categoria", as_index=False)["monto_abs_clp"]
        .sum()
        .sort_values("monto_abs_clp", ascending=False)
    )
    fig = px.pie(
        grouped,
        names="categoria",
        values="monto_abs_clp",
        color_discrete_sequence=PALETTE,
        hole=0.52,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), title="Distribucion por categoria")
    return fig


def category_frequency_chart(df: pd.DataFrame):
    if df.empty:
        return _empty_chart("Sin datos para frecuencia")

    grouped = (
        df.groupby("categoria", as_index=False)["id"]
        .count()
        .rename(columns={"id": "frecuencia"})
        .sort_values("frecuencia", ascending=False)
        .head(12)
    )
    fig = px.bar(
        grouped,
        x="categoria",
        y="frecuencia",
        color="categoria",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        title="Frecuencia por categoria",
        xaxis_title="Categoria",
        yaxis_title="Cantidad",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def weekday_chart(df: pd.DataFrame):
    if df.empty:
        return _empty_chart("Sin datos para dia de semana")

    weekdays = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo",
    }
    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    work["weekday"] = work["fecha"].dt.weekday
    grouped = work.groupby("weekday", as_index=False)["monto_abs_clp"].sum()
    grouped["dia"] = grouped["weekday"].map(weekdays)
    grouped = grouped.sort_values("weekday")

    fig = px.bar(grouped, x="dia", y="monto_abs_clp", color="dia", color_discrete_sequence=PALETTE)
    fig.update_layout(
        title="Gasto por dia de semana",
        xaxis_title="Dia",
        yaxis_title="Monto CLP",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def monthly_trend_chart(df: pd.DataFrame):
    if df.empty:
        return _empty_chart("Sin datos para tendencia mensual")

    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    grouped = (
        work.groupby(work["fecha"].dt.to_period("M"))["monto_abs_clp"]
        .sum()
        .reset_index()
        .rename(columns={"fecha": "periodo"})
    )
    grouped["periodo"] = grouped["periodo"].astype(str)
    fig = px.line(grouped, x="periodo", y="monto_abs_clp", markers=True)
    fig.update_traces(line_color="#0A0A0A", marker_color="#6366F1")
    fig.update_layout(
        title="Tendencia mensual",
        xaxis_title="Mes",
        yaxis_title="Monto CLP",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def projection_chart(df: pd.DataFrame):
    if df.empty:
        return _empty_chart("Sin categorias estables para proyectar")

    fig = px.bar(
        df,
        x="categoria",
        y="proyeccion",
        color="categoria",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        title="Proyeccion mensual por categorias estables",
        xaxis_title="Categoria",
        yaxis_title="Proyeccion CLP",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
