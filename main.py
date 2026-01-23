import base64
import os
import warnings
from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from flask_caching import Cache
from sqlalchemy import create_engine

from dash import (
    Dash,
    Input,
    Output,
    State,
    ctx,
    dcc,
    html,
)

warnings.filterwarnings("ignore")

# from dash.dependencies import Input, Output, State

load_dotenv()

host_psql = os.getenv("HOST_PSQL")
base_datos = os.getenv("BASE_DATOS")
usuario_psql = os.getenv("USUARIO_PSQL")
clave_psql = os.getenv("CLAVE_PSQL")


engine = create_engine(
    f"postgresql+psycopg2://{usuario_psql}:{clave_psql}@{host_psql}/{base_datos}"
)


# INICIALIZAR APP
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Cache en memoria
cache = Cache(
    server,
    config={
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 60 * 60 * 2,
    },
)


@cache.memoize()
def get_precios_por_dia():
    query = """
        SELECT *
        FROM vw_peco_ecommerce_antiparasitarios_daily
    """
    df = pd.read_sql(query, engine)
    df["fecha_dia"] = pd.to_datetime(df["fecha_dia"])
    return df


# Función auxiliar para crear variaciones
def crear_variacion_html(precio_actual, precio_anterior):
    """Crea el HTML para mostrar la variación con el día anterior"""
    if (
        precio_anterior is None
        or precio_actual == "-"
        or not isinstance(precio_actual, (int, float))
    ):
        return html.Span(
            "Sin dato anterior", style={"color": "gray", "fontSize": "10px"}
        )

    try:
        variacion = precio_actual - precio_anterior
        variacion_porcentaje = (
            (variacion / precio_anterior) * 100 if precio_anterior != 0 else 0
        )

        if variacion > 0:
            return html.Span(
                [
                    html.Span("📈 ", style={"color": "green"}),
                    f"+S/{variacion:.2f} ",
                    html.Span(
                        f"({variacion_porcentaje:.1f}%)",
                        style={"color": "green", "fontWeight": "bold"},
                    ),
                ]
            )
        elif variacion < 0:
            return html.Span(
                [
                    html.Span("📉 ", style={"color": "red"}),
                    f"S/{variacion:.2f} ",
                    html.Span(
                        f"({variacion_porcentaje:.1f}%)",
                        style={"color": "red", "fontWeight": "bold"},
                    ),
                ]
            )
        else:
            return html.Span(
                [html.Span("➡️ ", style={"color": "gray"}), "Sin cambio"]
            )
    except:
        return html.Span(
            "Error cálculo", style={"color": "orange", "fontSize": "10px"}
        )


# FUNCIÓN PRINCIPAL PARA CREAR GRÁFICOS
def crear_graficos(df_filtrado, df_comparativa=None):
    if len(df_filtrado) == 0:
        fig_vacio = go.Figure()
        fig_vacio.update_layout(
            title="No hay datos para los filtros seleccionados",
            xaxis_title="Fecha",
            yaxis_title="Precio",
            height=500,
        )
        estadisticas = html.P(
            "No hay datos para mostrar", className="text-danger"
        )
        tabla = html.P("No hay datos para mostrar", className="text-danger")
        tabla_comparativa = html.P(
            "No hay datos para mostrar", className="text-danger"
        )
        return (
            fig_vacio,
            fig_vacio,
            fig_vacio,
            estadisticas,
            tabla,
            tabla_comparativa,
        )

    # Gráfico principal - Evolución temporal
    df_prod = (
        df_filtrado.groupby(["fecha_dia", "descripcion_producto"])
        .agg({"promedio": "mean", "maximo": "max", "minimo": "min"})
        .reset_index()
        .sort_values("fecha_dia")
    )

    fig_principal = go.Figure()
    productos_unicos = sorted(df_prod["descripcion_producto"].unique())
    n_productos = len(productos_unicos)
    PALETA = px.colors.sequential.Blues
    if n_productos <= 8:
        colors = PALETA[-n_productos:]  # Los más oscuros al final
    else:
        positions = np.linspace(0.3, 1, n_productos)
        colors = px.colors.sample_colorscale(PALETA, positions)

    for idx, prod in enumerate(productos_unicos):
        df_i = df_prod[df_prod["descripcion_producto"] == prod]

        color = colors[idx % len(colors)]

        fig_principal.add_trace(
            go.Scatter(
                x=df_i["fecha_dia"],
                y=df_i["promedio"],
                mode="lines+markers",
                name=str(prod),
                line=dict(width=2, color=color),
                marker=dict(size=6, color=color, symbol="circle"),
                opacity=0.85,
                customdata=df_i[["maximo", "minimo", "promedio"]],
                hovertemplate="<b>%{fullData.name}</b><br>"
                + "Fecha: %{x|%d %b %Y}<br>"
                + "Prom: S/ %{customdata[2]:.2f}<br>"
                + "Máx: S/ %{customdata[0]:.2f}<br>"
                + "Mín: S/ %{customdata[1]:.2f}<br>"
                + "<extra></extra>",
            )
        )

    fig_principal.update_layout(
        title=f"Evolución de precios por producto ({n_productos} productos)",
        xaxis_title="Fecha",
        yaxis_title="Precio (S/)",
        hovermode="x unified",
        template="plotly_white",
        height=520,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
        margin=dict(b=120),
    )

    # Boxplot - Distribución de precios con tonos
    fig_boxplot = go.Figure()

    # O usando la paleta Blues:
    box_colors_blues = [
        px.colors.sequential.Blues[8],  # Azul oscuro
        px.colors.sequential.Blues[5],  # Azul medio
        px.colors.sequential.Blues[8],  # Azul claro
    ]

    for col, name, color in [
        ("maximo", "Máximo", box_colors_blues[0]),
        ("minimo", "Mínimo", box_colors_blues[1]),
        ("promedio", "Promedio", box_colors_blues[2]),
    ]:
        fig_boxplot.add_trace(
            go.Box(
                y=df_filtrado[col].dropna(),
                name=name,
                marker_color=color,
                boxmean=True,
                line=dict(color=color, width=2),
            )
        )

    fig_boxplot.update_layout(
        title="Distribución de Precios",
        yaxis_title="Precio (S/)",
        template="plotly_white",
        height=300,
        showlegend=False,
    )

    # Gráfico de conteo por día con Blues
    df_conteo = (
        df_filtrado.groupby("fecha_dia")["descripcion_producto"]
        .nunique()
        .reset_index(name="n_productos")
    )

    fig_conteo = go.Figure()
    fig_conteo.add_trace(
        go.Bar(
            x=df_conteo["fecha_dia"],
            y=df_conteo["n_productos"],
            name="Productos únicos",
            marker=dict(
                color=df_conteo["n_productos"],
                colorscale="Blues",  # Escala 100% azul
                showscale=True,
                colorbar=dict(
                    title="Cantidad",
                    thickness=15,
                    len=0.5,
                    tickfont=dict(size=10),
                ),
                line=dict(color="rgba(0,50,100,0.3)", width=0.5),
            ),
        )
    )

    fig_conteo.update_layout(
        title="Número de productos por día",
        xaxis_title="Fecha",
        yaxis_title="Cantidad de productos",
        template="plotly_white",
        height=300,
        showlegend=False,
    )

    # Estadísticas rápidas
    total_prod = df_filtrado["descripcion_producto"].nunique()
    total_dias = df_filtrado["fecha_dia"].nunique()
    precio_max_global = df_filtrado["maximo"].max()
    precio_min_global = df_filtrado["minimo"].min()
    precio_prom_global = df_filtrado["promedio"].mean()

    estadisticas = html.Div(
        [
            html.P(f"📦 Productos analizados: {total_prod}", className="mb-1"),
            html.P(f"📅 Días analizados: {total_dias}", className="mb-1"),
            html.P(
                f"💰 Precio máximo: S/ {precio_max_global:.2f}",
                className="mb-1",
            ),
            html.P(
                f"💰 Precio mínimo: S/ {precio_min_global:.2f}",
                className="mb-1",
            ),
            html.P(
                f"💰 Precio promedio: S/ {precio_prom_global:.2f}",
                className="mb-1",
            ),
            html.P(
                f"📊 Rango: S/ {precio_max_global - precio_min_global:.2f}",
                className="mb-1",
            ),
        ]
    )

    # Tabla top 10
    tabla_resumen = (
        df_filtrado.groupby(
            ["descripcion_producto", "presentacion_producto", "ecommerce"]
        )
        .agg({"promedio": "mean", "maximo": "max", "minimo": "min"})
        .reset_index()
        .sort_values("promedio", ascending=False)
        .head(10)
    )

    tabla_resumen = tabla_resumen.round({"promedio": 2})
    tabla_resumen = tabla_resumen.round({"maximo": 2})
    tabla_resumen = tabla_resumen.round({"minimo": 2})

    tabla = dbc.Table.from_dataframe(
        tabla_resumen, bordered=True, hover=True, responsive=True, size="sm"
    )

    # COMPARATIVA E-COMMERCE - Usar df_comparativa si está disponible
    df_comp = df_comparativa if df_comparativa is not None else df_filtrado

    if len(df_comp) > 0:
        # Obtener las 3 tiendas principales (o todas si hay menos de 3)
        todas_tiendas = sorted(df_comp["ecommerce"].dropna().unique())
        tiendas = (
            todas_tiendas[:3] if len(todas_tiendas) >= 3 else todas_tiendas
        )

        # Obtener la fecha más reciente
        fecha_mas_reciente = df_comp["fecha_dia"].max()
        fecha_anterior = fecha_mas_reciente - pd.Timedelta(days=1)

        # Filtrar datos del día más reciente
        df_hoy = df_comp[df_comp["fecha_dia"] == fecha_mas_reciente].copy()
        df_ayer = df_comp[df_comp["fecha_dia"] == fecha_anterior].copy()

        if len(df_hoy) == 0:
            tabla_comparativa = html.P(
                f"No hay datos para la fecha más reciente ({fecha_mas_reciente.date()})",
                className="text-warning",
            )
        else:
            # Crear tabla pivot con promedio por producto y tienda
            pivot_table = df_hoy.pivot_table(
                index="descripcion_producto",
                columns="ecommerce",
                values="promedio",
                aggfunc="mean",
            ).reset_index()

            # Asegurarse de que todas las tiendas estén presentes
            for tienda in tiendas:
                if tienda not in pivot_table.columns:
                    pivot_table[tienda] = "-"

            # Reordenar columnas para que las tiendas estén en el orden deseado
            column_order = ["descripcion_producto"] + tiendas
            pivot_table = pivot_table[column_order]
            pivot_table = pivot_table.fillna("-")

            # Calcular precios del día anterior para cada producto
            variaciones = {}
            if len(df_ayer) > 0:
                precios_ayer = (
                    df_ayer.groupby(["descripcion_producto", "ecommerce"])[
                        "promedio"
                    ]
                    .mean()
                    .reset_index()
                )
                for _, row in precios_ayer.iterrows():
                    producto = row["descripcion_producto"]
                    tienda = row["ecommerce"]
                    precio_ayer = row["promedio"]
                    if producto not in variaciones:
                        variaciones[producto] = {}
                    variaciones[producto][tienda] = precio_ayer

            # Generar la tabla HTML
            rows = []
            for _, row in pivot_table.iterrows():
                # Calcular máximos y mínimos solo para precios válidos
                precios_validos = [
                    row[tienda]
                    for tienda in tiendas
                    if row[tienda] != "-"
                    and isinstance(row[tienda], (int, float))
                ]

                if precios_validos:
                    max_val = max(precios_validos)
                    min_val = min(precios_validos)
                else:
                    max_val = 0
                    min_val = 0

                # Crear celdas para cada tienda
                celdas = []
                for tienda in tiendas:
                    value = row[tienda]

                    # Determinar si es el más caro o más barato
                    es_max = (
                        value != "-"
                        and isinstance(value, (int, float))
                        and value == max_val
                        and max_val != min_val
                    )
                    es_min = (
                        value != "-"
                        and isinstance(value, (int, float))
                        and value == min_val
                        and max_val != min_val
                    )

                    # Color de fondo basado en precio
                    if es_max:
                        bg_color = "#d4edda"  # Verde claro para más caro
                        color_bolita = "green"
                    elif es_min:
                        bg_color = "#fff3cd"  # Amarillo claro para más barato
                        color_bolita = "red"
                    elif value == "-":
                        bg_color = "#f8f9fa"  # Gris para sin dato
                        color_bolita = "transparent"
                    else:
                        bg_color = "white"
                        color_bolita = "transparent"

                    celda = html.Td(
                        [
                            # Contenedor principal
                            html.Div(
                                [
                                    # Fila 1: Bolita y precio
                                    html.Div(
                                        [
                                            # Bolita de color
                                            html.Div(
                                                style={
                                                    "width": "12px",
                                                    "height": "12px",
                                                    "borderRadius": "50%",
                                                    "backgroundColor": color_bolita,
                                                    "display": "inline-block",
                                                    "marginRight": "8px",
                                                    "verticalAlign": "middle",
                                                    "border": "1px solid #ddd"
                                                    if color_bolita
                                                    == "transparent"
                                                    else "none",
                                                }
                                            ),
                                            # Precio actual
                                            html.Span(
                                                f"S/ {value:.2f}"
                                                if value != "-"
                                                and pd.notna(value)
                                                else "-",
                                                style={
                                                    "fontWeight": "bold"
                                                    if es_max or es_min
                                                    else "normal",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                        ],
                                        style={"marginBottom": "5px"},
                                    ),
                                    # Fila 2: Variación
                                    html.Div(
                                        crear_variacion_html(
                                            value,
                                            variaciones.get(
                                                row["descripcion_producto"], {}
                                            ).get(tienda, None),
                                        )
                                    ),
                                ]
                            )
                        ],
                        style={
                            "textAlign": "center",
                            "padding": "8px",
                            "backgroundColor": bg_color,
                            "minWidth": "150px",
                            "border": "1px solid #dee2e6",
                            "verticalAlign": "middle",
                        },
                    )
                    celdas.append(celda)

                # Crear fila
                rows.append(
                    html.Tr(
                        [
                            html.Td(
                                row["descripcion_producto"],
                                style={
                                    "position": "sticky",
                                    "left": 0,
                                    "background": "white",
                                    "fontWeight": "bold",
                                    "zIndex": 1,
                                    "minWidth": "200px",
                                    "border": "1px solid #dee2e6",
                                },
                            )
                        ]
                        + celdas
                    )
                )

            tabla_comparativa_html = html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th(
                                    "Producto",
                                    style={
                                        "position": "sticky",
                                        "left": 0,
                                        "background": "white",
                                        "zIndex": 2,
                                        "minWidth": "200px",
                                        "border": "1px solid #dee2e6",
                                    },
                                )
                            ]
                            + [
                                html.Th(
                                    tienda,
                                    style={
                                        "textAlign": "center",
                                        "minWidth": "150px",
                                        "backgroundColor": "#f8f9fa",
                                        "border": "1px solid #dee2e6",
                                    },
                                )
                                for tienda in tiendas
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                style={
                    "width": "100%",
                    "borderCollapse": "collapse",
                    "fontSize": "13px",
                    "border": "1px solid #dee2e6",
                },
            )

            # Pie de tabla con información
            tabla_comparativa = html.Div(
                [
                    html.Div(
                        [
                            html.H6(
                                f"📊 Comparativa de Precios - {fecha_mas_reciente.strftime('%d/%m/%Y')}",
                                style={
                                    "textAlign": "center",
                                    "marginBottom": "10px",
                                    "color": "#0d6efd",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "🟢 = Precio más caro (entre tiendas)",
                                        style={
                                            "marginRight": "20px",
                                            "fontSize": "11px",
                                        },
                                    ),
                                    html.Span(
                                        "🔴 = Precio más barato (entre tiendas)",
                                        style={"fontSize": "11px"},
                                    ),
                                ],
                                style={
                                    "marginBottom": "8px",
                                    "textAlign": "center",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "📈 = Subió vs ayer",
                                        style={
                                            "marginRight": "15px",
                                            "fontSize": "10px",
                                            "color": "green",
                                        },
                                    ),
                                    html.Span(
                                        "📉 = Bajó vs ayer",
                                        style={
                                            "marginRight": "15px",
                                            "fontSize": "10px",
                                            "color": "red",
                                        },
                                    ),
                                    html.Span(
                                        "➡️ = Sin cambios/sin dato",
                                        style={
                                            "fontSize": "10px",
                                            "color": "gray",
                                        },
                                    ),
                                ],
                                style={
                                    "marginBottom": "15px",
                                    "textAlign": "center",
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        tabla_comparativa_html,
                        style={
                            "maxHeight": "400px",
                            "overflowY": "auto",
                            "border": "1px solid #dee2e6",
                        },
                    ),
                ]
            )
    else:
        tabla_comparativa = html.P(
            "No hay datos para comparar", className="text-danger"
        )

    return (
        fig_principal,
        fig_boxplot,
        fig_conteo,
        estadisticas,
        tabla,
        tabla_comparativa,
    )


def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def server_layout():
    df = get_precios_por_dia()
    logo_biomont = image_to_base64("dash/public/logo-biomont.png")
    return dbc.Container(
        [
            # Este componente dispara la carga inicial y las actualizaciones
            dcc.Interval(id="init", n_intervals=0, max_intervals=1),
            dcc.Store(id="store-df-version", data=0),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            align="center",
                                            children=[
                                                # Logo
                                                dbc.Col(
                                                    html.Img(
                                                        src=f"data:image/png;base64,{logo_biomont}",
                                                        style={
                                                            "height": "46px"
                                                        },
                                                    ),
                                                    width="auto",
                                                ),
                                                # Título
                                                dbc.Col(
                                                    [
                                                        html.H4(
                                                            "Monitoreo de Precios en E-commerce",
                                                            className="fw-bold text-primary mb-0",
                                                        ),
                                                        html.Small(
                                                            "Business Intelligence",
                                                            className="text-muted",
                                                        ),
                                                    ]
                                                ),
                                                # Metadata derecha
                                                dbc.Col(
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                "Actualización diaria",
                                                                className="text-muted small",
                                                            ),
                                                            html.Div(
                                                                "Fuente: Scraping e-commerce",
                                                                className="text-muted small",
                                                            ),
                                                        ],
                                                        className="text-end",
                                                    ),
                                                    width="auto",
                                                ),
                                            ],
                                        )
                                    ]
                                ),
                                className="shadow-sm border-0",
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            dbc.Col(
                [
                    dbc.Button(
                        [
                            html.I(className="fas fa-sync-alt"),
                            " Actualizar Datos",
                        ],
                        id="btn-actualizar",
                        color="primary",
                        outline=True,
                        className="me-1",
                    ),
                ],
                className="block mb-4",
            ),
            # Filtros principales, sección 1
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "🔍 Filtros Principales",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Label(
                                                "Nombre del Producto:",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-nombre-producto",
                                                options=[
                                                    {
                                                        "label": str(prod),
                                                        "value": prod,
                                                    }
                                                    for prod in sorted(
                                                        df["nombre_producto"]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value=[],
                                                multi=True,
                                                placeholder="Selecciona uno o varios productos...",
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                "Producto Bulk:",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-bulk",
                                                options=[
                                                    {
                                                        "label": "Todos",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(bio),
                                                        "value": bio,
                                                    }
                                                    for bio in sorted(
                                                        df["segmento_producto"]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona producto bulk...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                "Presentación:",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-presentacion",
                                                options=[
                                                    {
                                                        "label": "Todas",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(pres),
                                                        "value": pres,
                                                    }
                                                    for pres in sorted(
                                                        df[
                                                            "presentacion_producto"
                                                        ]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona presentación...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                "Subcategoría",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-subcategoria",
                                                options=[
                                                    {
                                                        "label": "Todas",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(sub),
                                                        "value": sub,
                                                    }
                                                    for sub in sorted(
                                                        df[
                                                            "subcategoria_producto"
                                                        ]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona subcategoría...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                "Especie Destino:",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-especie",
                                                options=[
                                                    {
                                                        "label": "Todas",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(esp),
                                                        "value": esp,
                                                    }
                                                    for esp in sorted(
                                                        df[
                                                            "especie_destino_producto"
                                                        ]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona especie...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            # Aplicar filtros
                                            dbc.Button(
                                                "🔄 Aplicar Filtros",
                                                id="btn-aplicar-filtros",
                                                color="primary",
                                                className="w-100 mt-3",
                                                n_clicks=0,
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=3,
                    ),
                    # Gráfico temporal, sección 2
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "📈 Evolución Temporal de Precios",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="grafico-principal",
                                                style={"height": "600px"},
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                    # Otros filtros, sección 3
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "⚙️ Filtros Adicionales",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Label(
                                                "E-commerce:",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-ecommerce",
                                                options=[
                                                    {
                                                        "label": "Todos",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(eco),
                                                        "value": eco,
                                                    }
                                                    for eco in sorted(
                                                        df["ecommerce"]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona e-commerce...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                "Rango de Fechas:",
                                                className="fw-bold",
                                            ),
                                            dcc.DatePickerRange(
                                                id="filtro-fechas",
                                                min_date_allowed=df[
                                                    "fecha_dia"
                                                ].min(),
                                                max_date_allowed=df[
                                                    "fecha_dia"
                                                ].max(),
                                                start_date=df["fecha_dia"].max()
                                                - timedelta(days=30),
                                                end_date=df["fecha_dia"].max(),
                                                className="mb-3 w-100",
                                            ),
                                            html.Label(
                                                "Marca:", className="fw-bold"
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-marca",
                                                options=[
                                                    {
                                                        "label": "Todas",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(marca),
                                                        "value": marca,
                                                    }
                                                    for marca in sorted(
                                                        df["marca_producto"]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona marca...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            html.Label(
                                                "Producto Biomont:",
                                                className="fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="filtro-biomont",
                                                options=[
                                                    {
                                                        "label": "Todos",
                                                        "value": "ALL",
                                                    }
                                                ]
                                                + [
                                                    {
                                                        "label": str(bio),
                                                        "value": bio,
                                                    }
                                                    for bio in sorted(
                                                        df["biomont_producto"]
                                                        .dropna()
                                                        .unique()
                                                    )
                                                ],
                                                value="ALL",
                                                placeholder="Selecciona biomont...",
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            # Botón para limpiar filtros
                                            dbc.Button(
                                                "🧹 Limpiar Filtros",
                                                id="btn-limpiar-filtros",
                                                color="secondary",
                                                className="w-100 mt-2",
                                                n_clicks=0,
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-4",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "📊 Estadísticas Rápidas",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="estadisticas-rapidas",
                                                className="small",
                                            )
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            # Segunda fila: Nueva tabla comparativa
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "🏪 Comparativa de Precios por E-commerce",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="tabla-comparativa",
                                                style={"overflowX": "auto"},
                                            )
                                        ]
                                    ),
                                    dbc.CardFooter(
                                        "Comparativa del día más reciente disponible. Los precios son promedios diarios.",
                                        className="text-muted small",
                                    ),
                                ]
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Tercer fila: Gráficos adicionales
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "📉 Distribución de Precios",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="grafico-boxplot",
                                                style={"height": "300px"},
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "🔢 Conteo de SKUs por Día",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="grafico-conteo",
                                                style={"height": "300px"},
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                ],
                className="mb-4",
            ),
            # Cuarta fila: Tabla de datos original
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "📋 Datos Detallados",
                                        className="fw-bold",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Div(id="tabla-datos"),
                                            html.Div(
                                                [
                                                    dbc.Button(
                                                        "📥 Descargar CSV",
                                                        id="btn-descargar",
                                                        color="success",
                                                        className="mt-3 w-100",
                                                    ),
                                                    dcc.Download(
                                                        id="download-dataframe-csv"
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=12,
                    )
                ]
            ),
            # Almacenar estado de los filtros
            dcc.Store(id="store-filtros-aplicados", data={"aplicado": False}),
        ],
        fluid=True,
    )


# LAYOUT DASH
app.layout = server_layout()

# CALLBACKS ########################################################################


# Callback para limpiar los filtros
@app.callback(
    [
        Output("filtro-nombre-producto", "value"),
        Output("filtro-subcategoria", "value"),
        Output("filtro-biomont", "value"),
        Output("filtro-bulk", "value"),
        Output("filtro-presentacion", "value"),
        Output("filtro-especie", "value"),
        Output("filtro-ecommerce", "value"),
        Output("filtro-marca", "value"),
        Output("filtro-fechas", "start_date"),
        Output("filtro-fechas", "end_date"),
    ],
    Input("btn-limpiar-filtros", "n_clicks"),
    prevent_initial_call=True,
)
def limpiar_filtros(n_clicks):
    df = get_precios_por_dia()
    fecha_max = df["fecha_dia"].max()
    fecha_inicio = fecha_max - timedelta(days=30)

    return (
        [],
        "ALL",
        "ALL",
        "ALL",
        "ALL",
        "ALL",
        "ALL",
        "ALL",
        fecha_inicio.strftime("%Y-%m-%d"),
        fecha_max.strftime("%Y-%m-%d"),
    )


@app.callback(
    [
        Output("filtro-nombre-producto", "options"),
        Output("filtro-subcategoria", "options"),
        Output("filtro-biomont", "options"),
        Output("filtro-bulk", "options"),
        Output("filtro-presentacion", "options"),
        Output("filtro-especie", "options"),
        Output("filtro-ecommerce", "options"),
        Output("filtro-marca", "options"),
        Output("filtro-fechas", "min_date_allowed"),
        Output("filtro-fechas", "max_date_allowed"),
        Output("store-df-version", "data"),
    ],
    Input("btn-actualizar", "n_clicks"),
    prevent_initial_call=True,
)
def actualizar_opciones(_):
    cache.delete_memoized(get_precios_por_dia)
    df = get_precios_por_dia()

    return (
        [
            {"label": str(p), "value": p}
            for p in sorted(df["nombre_producto"].dropna().unique())
        ],
        [{"label": "Todas", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["subcategoria_producto"].dropna().unique())
        ],
        [{"label": "Todos", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["biomont_producto"].dropna().unique())
        ],
        [{"label": "Todos", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["segmento_producto"].dropna().unique())
        ],
        [{"label": "Todas", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["presentacion_producto"].dropna().unique())
        ],
        [{"label": "Todas", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["especie_destino_producto"].dropna().unique())
        ],
        [{"label": "Todos", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["ecommerce"].dropna().unique())
        ],
        [{"label": "Todas", "value": "ALL"}]
        + [
            {"label": str(x), "value": x}
            for x in sorted(df["marca_producto"].dropna().unique())
        ],
        df["fecha_dia"].min(),
        df["fecha_dia"].max(),
        datetime.now().timestamp(),  # fuerza downstream callbacks
    )


# Callback principal - MODIFICADO
@app.callback(
    [
        Output("grafico-principal", "figure"),
        Output("grafico-boxplot", "figure"),
        Output("grafico-conteo", "figure"),
        Output("estadisticas-rapidas", "children"),
        Output("tabla-datos", "children"),
        Output("tabla-comparativa", "children"),
        Output("store-filtros-aplicados", "data"),
    ],
    [
        Input("init", "n_intervals"),
        Input("btn-actualizar", "n_clicks"),
        Input("btn-aplicar-filtros", "n_clicks"),
        Input("btn-limpiar-filtros", "n_clicks"),
    ],
    [
        State("filtro-nombre-producto", "value"),
        State("filtro-subcategoria", "value"),
        State("filtro-biomont", "value"),
        State("filtro-presentacion", "value"),
        State("filtro-especie", "value"),
        State("filtro-ecommerce", "value"),
        State("filtro-marca", "value"),
        State("filtro-bulk", "value"),
        State("filtro-fechas", "start_date"),
        State("filtro-fechas", "end_date"),
    ],
)
def update_dashboard(
    _,
    n_clicks_actualizar,
    n_clicks_aplicar,
    n_clicks_limpiar,
    nombre_producto,
    subcategoria,
    biomont,
    presentacion,
    especie,
    ecommerce,
    marca,
    filtro_bulk,
    start_date,
    end_date,
):
    df = get_precios_por_dia()
    trigger = ctx.triggered_id

    # Carga inicial
    if trigger in (None, "init"):
        fecha_max = df["fecha_dia"].max()
        fecha_inicio = fecha_max - timedelta(days=30)

        df_filtrado = df[
            (df["fecha_dia"] >= fecha_inicio) & (df["fecha_dia"] <= fecha_max)
        ]

        (
            fig_principal,
            fig_boxplot,
            fig_conteo,
            estadisticas,
            tabla,
            tabla_comparativa,
        ) = crear_graficos(df_filtrado)

        filtros = {
            "aplicado": True,
            "tipo": "inicial",
            "nombre_producto": [],
            "subcategoria": "ALL",
            "biomont": "ALL",
            "presentacion": "ALL",
            "especie": "ALL",
            "ecommerce": "ALL",
            "marca": "ALL",
            "segmento_producto": "ALL",
            "start_date": fecha_inicio.strftime("%Y-%m-%d"),
            "end_date": fecha_max.strftime("%Y-%m-%d"),
        }

        return (
            fig_principal,
            fig_boxplot,
            fig_conteo,
            estadisticas,
            tabla,
            tabla_comparativa,
            filtros,
        )

    elif trigger == "btn-actualizar":
        cache.delete_memoized(get_precios_por_dia)
        df = get_precios_por_dia()

    # Para gráficos principales: aplicar TODOS los filtros incluyendo e-commerce
    df_filtrado = df.copy()

    if nombre_producto:
        df_filtrado = df_filtrado[
            df_filtrado["nombre_producto"].isin(nombre_producto)
        ]

    if subcategoria != "ALL":
        df_filtrado = df_filtrado[
            df_filtrado["subcategoria_producto"] == subcategoria
        ]
    if biomont != "ALL":
        df_filtrado = df_filtrado[df_filtrado["biomont_producto"] == biomont]
    if presentacion != "ALL":
        df_filtrado = df_filtrado[
            df_filtrado["presentacion_producto"] == presentacion
        ]
    if especie != "ALL":
        df_filtrado = df_filtrado[
            df_filtrado["especie_destino_producto"] == especie
        ]
    if ecommerce != "ALL":
        df_filtrado = df_filtrado[df_filtrado["ecommerce"] == ecommerce]
    if marca != "ALL":
        df_filtrado = df_filtrado[df_filtrado["marca_producto"] == marca]
    if filtro_bulk != "ALL":
        df_filtrado = df_filtrado[
            df_filtrado["segmento_producto"] == filtro_bulk
        ]

    if start_date and end_date:
        df_filtrado = df_filtrado[
            (df_filtrado["fecha_dia"] >= pd.to_datetime(start_date))
            & (df_filtrado["fecha_dia"] <= pd.to_datetime(end_date))
        ]

    # Para la tabla comparativa: NO APLICAR FILTRO DE E-COMMERCE
    df_comparativa = df.copy()

    if nombre_producto:
        df_comparativa = df_comparativa[
            df_comparativa["nombre_producto"].isin(nombre_producto)
        ]
    if subcategoria != "ALL":
        df_comparativa = df_comparativa[
            df_comparativa["subcategoria_producto"] == subcategoria
        ]
    if biomont != "ALL":
        df_comparativa = df_comparativa[
            df_comparativa["biomont_producto"] == biomont
        ]
    if presentacion != "ALL":
        df_comparativa = df_comparativa[
            df_comparativa["presentacion_producto"] == presentacion
        ]
    if especie != "ALL":
        df_comparativa = df_comparativa[
            df_comparativa["especie_destino_producto"] == especie
        ]
    # IMPORTANTE: NO aplicar filtro de ecommerce aquí para ver todas las tiendas
    # if ecommerce != 'ALL':
    #     df_comparativa = df_comparativa[df_comparativa['ecommerce'] == ecommerce]
    if marca != "ALL":
        df_comparativa = df_comparativa[
            df_comparativa["marca_producto"] == marca
        ]
    if filtro_bulk != "ALL":
        df_comparativa = df_comparativa[
            df_comparativa["segmento_producto"] == filtro_bulk
        ]

    if start_date and end_date:
        df_comparativa = df_comparativa[
            (df_comparativa["fecha_dia"] >= pd.to_datetime(start_date))
            & (df_comparativa["fecha_dia"] <= pd.to_datetime(end_date))
        ]

    # Crear gráficos con ambos DataFrames
    (
        fig_principal,
        fig_boxplot,
        fig_conteo,
        estadisticas,
        tabla,
        tabla_comparativa,
    ) = crear_graficos(df_filtrado, df_comparativa)

    filtros = {
        "aplicado": True,
        "tipo": trigger,
        "nombre_producto": nombre_producto,
        "subcategoria": subcategoria,
        "biomont": biomont,
        "presentacion": presentacion,
        "especie": especie,
        "ecommerce": ecommerce,
        "marca": marca,
        "segmento_producto": filtro_bulk,
        "start_date": start_date,
        "end_date": end_date,
    }

    return (
        fig_principal,
        fig_boxplot,
        fig_conteo,
        estadisticas,
        tabla,
        tabla_comparativa,
        filtros,
    )


# Callback descarga csv
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-descargar", "n_clicks"),
    State("store-filtros-aplicados", "data"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, filtros):
    df = get_precios_por_dia()

    if filtros and filtros["aplicado"]:
        df_descarga = df.copy()
        if filtros["nombre_producto"] and len(filtros["nombre_producto"]) > 0:
            df_descarga = df_descarga[
                df_descarga["nombre_producto"].isin(filtros["nombre_producto"])
            ]
        if filtros["subcategoria"] != "ALL":
            df_descarga = df_descarga[
                df_descarga["subcategoria_producto"] == filtros["subcategoria"]
            ]
        if filtros["biomont"] != "ALL":
            df_descarga = df_descarga[
                df_descarga["biomont_producto"] == filtros["biomont"]
            ]
        if filtros["presentacion"] != "ALL":
            df_descarga = df_descarga[
                df_descarga["presentacion_producto"] == filtros["presentacion"]
            ]
        if filtros["especie"] != "ALL":
            df_descarga = df_descarga[
                df_descarga["especie_destino_producto"] == filtros["especie"]
            ]
        if filtros["ecommerce"] != "ALL":
            df_descarga = df_descarga[
                df_descarga["ecommerce"] == filtros["ecommerce"]
            ]
        if filtros["marca"] != "ALL":
            df_descarga = df_descarga[
                df_descarga["marca_producto"] == filtros["marca"]
            ]
        if filtros.get("segmento_producto", "ALL") != "ALL":
            df_descarga = df_descarga[
                df_descarga["segmento_producto"] == filtros["segmento_producto"]
            ]
        if filtros["start_date"] and filtros["end_date"]:
            df_descarga = df_descarga[
                (
                    df_descarga["fecha_dia"]
                    >= pd.to_datetime(filtros["start_date"])
                )
                & (
                    df_descarga["fecha_dia"]
                    <= pd.to_datetime(filtros["end_date"])
                )
            ]

        # Ordenar por fecha y sku
        df_descarga = df_descarga.sort_values(["fecha_dia", "sku"])

        # Descargar csv
        return dcc.send_data_frame(
            df_descarga.to_csv, "precios_filtrados_completos.csv", index=False
        )
    else:
        df_completo = df.copy().sort_values(["fecha_dia", "sku"])
        return dcc.send_data_frame(
            df_completo.to_csv, "precios_completos.csv", index=False
        )


# EJECUTAR APP
if __name__ == "__main__":
    app.run(debug=True)
