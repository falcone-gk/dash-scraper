import marimo

__generated_with = "0.19.4"
app = marimo.App(
    width="medium",
    app_title=" Monitoreo de Precios en E-commerce ",
    css_file="assets/css/index.css",
    html_head_file="assets/html/head.html",
)


@app.cell
def _():
    import os
    import warnings
    from datetime import timedelta
    import math

    import marimo as mo
    import pandas as pd
    import plotly.graph_objects as go
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    warnings.filterwarnings("ignore")
    return create_engine, go, load_dotenv, math, mo, os, pd, timedelta


@app.cell
def _(create_engine, load_dotenv, os):
    # load data

    load_dotenv()

    host_psql = os.getenv("HOST_PSQL")
    base_datos = os.getenv("BASE_DATOS")
    usuario_psql = os.getenv("USUARIO_PSQL")
    clave_psql = os.getenv("CLAVE_PSQL")

    engine = create_engine(
        f"postgresql+psycopg2://{usuario_psql}:{clave_psql}@{host_psql}/{base_datos}"
    )
    return (engine,)


@app.cell
def _(mo):
    def custom_card(title, content, width="400px"):
        """
        Genera una tarjeta con encabezado estilizado y cuerpo de contenido usando Tailwind v4.
        """

        # Encabezado (HTML puro con clases Tailwind v4)
        header = mo.Html(f"""
        <div class="bg-slate-50 px-4 py-3 border-b border-slate-200">
            <h2 class="text-base font-semibold text-slate-800 m-0">
                {title}
            </h2>
        </div>
        """)

        # Cuerpo de la Card (Componente marimo)
        body_items = [content] if not isinstance(content, list) else content
        body = mo.vstack(body_items, gap=1).style({"padding": "20px"})

        # Contenedor Principal (Componente marimo)
        return mo.vstack(
            [header, body], gap=0
        ).style(
            {
                "max-width": width,
                "background-color": "white",
                "border": "1px solid var(--slate-200)",  # Tailwind v4 usa variables CSS internamente
                "border-radius": "12px",
                "box-shadow": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
                "overflow": "hidden",
                "margin-bottom": "20px",
            }
        )
    return (custom_card,)


@app.cell
def _(pd):
    def filter_equals(df, column, value, all_value="ALL"):
        if value is None or value == all_value:
            return df
        return df[df[column] == value]

    def filter_isin(df, column, values):
        if not values:
            return df
        return df[df[column].isin(values)]

    def filter_date_range(df, column, start_date, end_date):
        if not start_date or not end_date:
            return df

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        return df[(df[column] >= start) & (df[column] <= end)]

    def apply_filters(
        df,
        *,
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
        apply_ecommerce=True,  # 👈 clave para comparativa
    ):
        return (
            df.copy()
            .pipe(filter_isin, "nombre_producto", nombre_producto)
            .pipe(filter_equals, "subcategoria_producto", subcategoria)
            .pipe(filter_equals, "biomont_producto", biomont)
            .pipe(filter_equals, "presentacion_producto", presentacion)
            .pipe(filter_equals, "especie_destino_producto", especie)
            .pipe(
                filter_equals,
                "ecommerce",
                ecommerce if apply_ecommerce else "ALL",
            )
            .pipe(filter_equals, "marca_producto", marca)
            .pipe(filter_equals, "segmento_producto", filtro_bulk)
            .pipe(filter_date_range, "fecha_dia", start_date, end_date)
        )
    return (apply_filters,)


@app.cell
def _(go):
    # Main figure
    def get_fig_principal(df_filtrado):
        df_prod = (
            df_filtrado.groupby(["fecha_dia", "descripcion_producto"])
            .agg({"promedio": "mean", "maximo": "max", "minimo": "min"})
            .reset_index()
            .sort_values("fecha_dia")
        )

        fig_principal = go.Figure()

        for prod, df_i in df_prod.groupby("descripcion_producto"):
            fig_principal.add_trace(
                go.Scatter(
                    x=df_i["fecha_dia"],
                    y=df_i["promedio"],
                    mode="lines+markers",
                    name=str(prod),
                    line=dict(width=2),
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
            title=f"Evolución de precios por producto ({df_prod['descripcion_producto'].nunique()} productos)",
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

        return fig_principal
    return (get_fig_principal,)


@app.cell
def _(mo):
    logo = mo.image("dash/public/logo-biomont.png", height="80px")
    return (logo,)


@app.cell
def _(logo, mo):
    mo.md(f"""
    <div class="bg-white rounded-xl shadow-sm border-none mb-12">
      <div class="px-6 py-2">
        <div class="flex items-center gap-4">
          <div class="flex-none flex items-center">
            {logo}
          </div>
          <div class="flex-1 flex flex-col justify-center">
            <h1 class="text-4xl font-bold text-blue-700 leading-tight mb-0">
              Monitoreo de Precios en E-commerce
            </h1>
            <small class="text-gray-500 text-sm">Business Intelligence</small>
          </div>
          <div class="flex-none text-right flex flex-col justify-center">
            <div class="text-gray-500 text-sm">Actualización diaria</div>
            <div class="text-gray-500 text-sm">Fuente: Scraping e-commerce</div>
          </div>
        </div>
      </div>
    </div>
    """)
    return


@app.cell
def _(engine, mo, pd):
    @mo.cache
    def get_updated_dataframe():
        query = """
        SELECT *
        FROM vw_peco_ecommerce_antiparasitarios_daily
        """
        data = pd.read_sql(query, engine)
        data["fecha_dia"] = pd.to_datetime(data["fecha_dia"])

        return data
    return (get_updated_dataframe,)


@app.cell
def button_marimo(mo):
    refresh = mo.ui.run_button(label="🔄 Actualizar datos", kind="info")

    refresh
    return (refresh,)


@app.cell
def _(get_updated_dataframe, refresh):
    if refresh.value:
        get_updated_dataframe.cache_clear()

    df = get_updated_dataframe()
    return (df,)


@app.cell
def button_marimo_1(mo):
    el_clear = mo.ui.run_button(label="🧹 Limpiar Filtros", full_width=True)

    el_apply = mo.ui.run_button(
        label="🔄 Aplicar Filtros",
        kind="info",
        full_width=True
    )
    return (el_clear,)


@app.cell
def _(df):
    # Left card

    products_opts = df["nombre_producto"].dropna().unique()

    bulk_opts = {"Todos": "ALL"}
    bulk_opts.update(
        {str(bio): bio for bio in df["segmento_producto"].dropna().unique()}
    )

    pres_opts = {"Todos": "ALL"}
    pres_opts.update(
        {
            str(pres): pres
            for pres in df["presentacion_producto"].dropna().unique()
        }
    )

    sub_opts = {"Todos": "ALL"}
    sub_opts.update(
        {str(sub): sub for sub in df["subcategoria_producto"].dropna().unique()}
    )

    esp_opts = {"Todos": "ALL"}
    esp_opts.update(
        {
            str(esp): esp
            for esp in df["especie_destino_producto"].dropna().unique()
        }
    )
    return bulk_opts, esp_opts, pres_opts, products_opts, sub_opts


@app.cell
def _(df, timedelta):
    # Right card (filtros adicionales)

    # Dropdown ecommerce
    ecommerce_opts = {"Todos": "ALL"}
    ecommerce_opts.update(
        {str(eco): eco for eco in df["ecommerce"].dropna().unique()}
    )

    # date range
    max_date = df["fecha_dia"].max().date()
    start_date = max_date - timedelta(days=30)
    end_date = max_date

    # Dropdown marcas
    marca_opts = {"Todos": "ALL"}
    marca_opts.update(
        {str(marca): marca for marca in df["marca_producto"].dropna().unique()}
    )

    # Dropdown prod_biom
    prod_biom = {"Todos": "ALL"}
    prod_biom.update(
        {
            str(marca): marca
            for marca in df["biomont_producto"].dropna().unique()
        }
    )
    return ecommerce_opts, end_date, marca_opts, prod_biom, start_date


@app.cell
def _(custom_card, mo):
    # Card de estadistica
    def render_stats_card(df_filtrado):
        if df_filtrado.empty:
            return custom_card("📊 Estadísticas Rápidas", mo.md("Sin datos"))

        # Cálculos
        total_prod = df_filtrado["descripcion_producto"].nunique()
        total_dias = df_filtrado["fecha_dia"].nunique()
        p_max = df_filtrado["maximo"].max()
        p_min = df_filtrado["minimo"].min()
        p_prom = df_filtrado["promedio"].mean()

        # Creamos una lista de elementos sin bullets
        # Usamos mo.md para cada línea para tener negritas fáciles
        items = [
            mo.md(f"📦 Productos analizados: {total_prod}"),
            mo.md(f"📅 Días analizados: {total_dias}"),
            mo.md(f"💰 Precio máximo: S/ {p_max:,.2f}"),
            mo.md(f"💰 Precio mínimo: S/ {p_min:,.2f}"),
            mo.md(f"💰 Precio promedio: S/ {p_prom:,.2f}"),
            mo.md(f"📊 Rango: S/ {p_max - p_min:,.2f}"),
        ]

        # Agrupamos verticalmente con un gap pequeño (simulando mb-1 de Bootstrap)
        return custom_card(
            title="📊 Estadísticas Rápidas", content=mo.vstack(items, gap=0.5)
        )
    return (render_stats_card,)


@app.cell
def _(
    bulk_opts,
    ecommerce_opts,
    el_clear,
    end_date,
    esp_opts,
    marca_opts,
    mo,
    pres_opts,
    prod_biom,
    products_opts,
    start_date,
    sub_opts,
):
    # Se refencia el boton de limpiar filtros para restaurar todo a su estado inicial
    el_clear

    el_products = mo.ui.multiselect(
        options=products_opts, label="Nombre del Producto:", full_width=True
    )
    el_bulk = mo.ui.dropdown(
        options=bulk_opts,
        label="Producto Bulk:",
        value="Todos",
        full_width=True,
    )
    el_pres = mo.ui.dropdown(
        options=pres_opts, label="Presentación:", value="Todos", full_width=True
    )
    el_sub = mo.ui.dropdown(
        options=sub_opts, label="Subcategoría:", value="Todos", full_width=True
    )
    el_esp = mo.ui.dropdown(
        options=esp_opts,
        label="Especie Destino:",
        value="Todos",
        full_width=True,
    )
    el_ecommerce = mo.ui.dropdown(
        options=ecommerce_opts,
        label="E-commerce:",
        value="Todos",
        full_width=True,
    )
    el_date_range = mo.ui.date_range(start=start_date, stop=end_date, label="Rango de Fechas:", full_width=True)
    el_marca = mo.ui.dropdown(
        options=marca_opts, label="Marca:", value="Todos", full_width=True
    )
    el_prod_biom = mo.ui.dropdown(
        options=prod_biom,
        label="Producto Biomont:",
        value="Todos",
        full_width=True,
    )
    return (
        el_bulk,
        el_date_range,
        el_ecommerce,
        el_esp,
        el_marca,
        el_pres,
        el_prod_biom,
        el_products,
        el_sub,
    )


@app.cell
def _(
    apply_filters,
    df,
    el_bulk,
    el_date_range,
    el_ecommerce,
    el_esp,
    el_marca,
    el_pres,
    el_prod_biom,
    el_products,
    el_sub,
):
    df_filtered = apply_filters(
        df,
        nombre_producto=el_products.value,
        subcategoria=el_sub.value,
        biomont=el_prod_biom.value,
        presentacion=el_pres.value,
        especie=el_esp.value,
        ecommerce=el_ecommerce.value,
        marca=el_marca.value,
        filtro_bulk=el_bulk.value,
        start_date=el_date_range.value[0],
        end_date=el_date_range.value[1],
    )
    return (df_filtered,)


@app.cell
def _(df_filtered, el_clear, render_stats_card):
    el_clear

    # Construcción del contenido con Markdown (scannable y limpio)
    # Usamos f-strings para inyectar los valores formateados
    el_stats = render_stats_card(df_filtered)
    return (el_stats,)


@app.cell
def _(
    custom_card,
    el_bulk,
    el_clear,
    el_date_range,
    el_ecommerce,
    el_esp,
    el_marca,
    el_pres,
    el_prod_biom,
    el_products,
    el_sub,
):
    # Cards de filtros
    card_filtros = custom_card(
        title="🔍 Filtros Principales",
        content=[
            el_products,
            el_bulk,
            el_pres,
            el_sub,
            el_esp,
            # No se necesita porque los selects actualizan todo solos
            # el_apply,
        ],
    )

    card_filtros_ad = custom_card(
        title="⚙️ Filtros Adicionales",
        content=[el_ecommerce, el_date_range, el_marca, el_prod_biom, el_clear],
    )
    return card_filtros, card_filtros_ad


@app.cell
def _(custom_card, df_filtered, get_fig_principal, mo):
    fig_1 = get_fig_principal(df_filtered)
    main_fig = mo.ui.plotly(fig_1)
    card_main_fig = custom_card(
        title="📈 Evolución Temporal de Precios", content=main_fig, width="100%"
    )
    return (card_main_fig,)


@app.cell
def _(card_filtros, card_filtros_ad, card_main_fig, el_stats, mo):
    left_side = mo.vstack([card_filtros_ad, el_stats])
    mo.hstack(
        [card_filtros, card_main_fig, left_side],
        widths=[2, 6, 2],
        gap=2,
        align="start",
    )
    return


@app.cell
def _(math, mo):
    def crear_variacion_html(precio_actual, precio_anterior):
        """Crea el HTML para mostrar la variación con el día anterior en marimo"""

        es_nan_actual = isinstance(precio_actual, float) and math.isnan(precio_actual)

        # Validaciones iniciales
        if (
            precio_anterior is None
            or math.isnan(precio_anterior)
            or precio_actual == "-"
            or es_nan_actual
            or not isinstance(precio_actual, (int, float))
        ):
            return mo.Html(
                '<span class="text-gray-400 text-[10px]">Sin dato anterior</span>'
            )

        try:
            # Cálculos
            variacion: float = float(precio_actual) - precio_anterior
            variacion_porcentaje: float = (
                (variacion / precio_anterior) * 100
                if precio_anterior != 0
                else 0
            )

            # Lógica de estilos según tendencia
            # Evitar problemas de precisión de punto flotante
            if variacion > 0:
                color_class = "text-emerald-600"
                icon = "📈"
                texto_variacion = f"+S/{variacion:.2f}"
            elif variacion < 0:
                color_class = "text-red-600"
                icon = "📉"
                texto_variacion = f"S/{variacion:.2f}"
            else:
                return mo.Html(
                    '<span class="text-gray-500 text-xs">➡️ Sin cambio</span>'
                )

            return mo.Html(
                f"""
                <span class="text-[11px] whitespace-nowrap text-slate-700">
                    <span class="{color_class}">{icon}</span>
                    {texto_variacion}
                    <span class="{color_class} font-bold">({variacion_porcentaje:.1f}%)</span>
                </span>
                """
            )

        except Exception:
            return mo.Html(
                '<span class="text-amber-500 text-[10px]">Error cálculo</span>'
            )
    return (crear_variacion_html,)


@app.cell
def _(crear_variacion_html, mo, pd):
    def render_comparativa_ecommerce(df_comp):
        if df_comp is None or len(df_comp) == 0:
            return mo.md("⚠️ No hay datos para comparar")

        # Preparación de Fechas y Tiendas
        todas_tiendas = sorted(
            df_comp["ecommerce"].dropna().unique()
        )
        tiendas = (
            todas_tiendas[:3] if len(todas_tiendas) >= 3 else todas_tiendas
        )

        fecha_mas_reciente = df_comp["fecha_dia"].max()
        fecha_anterior = fecha_mas_reciente - pd.Timedelta(days=1)

        df_hoy = df_comp[df_comp["fecha_dia"] == fecha_mas_reciente].copy()
        df_ayer = df_comp[df_comp["fecha_dia"] == fecha_anterior].copy()

        if len(df_hoy) == 0:
            return mo.md(
                f"⚠️ No hay datos para la fecha {fecha_mas_reciente.date()}"
            )

        # Pivot Table
        pivot_table = df_hoy.pivot_table(
            index="nombre_producto",
            columns="ecommerce",
            values="promedio",
            aggfunc="mean",
        ).reset_index()

        for tienda in tiendas:
            if tienda not in pivot_table.columns:
                pivot_table[tienda] = "-"

        pivot_table = pivot_table[["nombre_producto"] + tiendas]

        # Variaciones vs Ayer
        variaciones = {}
        if not df_ayer.empty:
            precios_ayer = (
                df_ayer.groupby(["nombre_producto", "ecommerce"])["promedio"]
                .mean()
                .reset_index()
            )
            for _, row in precios_ayer.iterrows():
                prod, tienda, p_ayer = (
                    row["nombre_producto"],
                    row["ecommerce"],
                    row["promedio"],
                )
                if prod not in variaciones:
                    variaciones[prod] = {}
                variaciones[prod][tienda] = p_ayer

        # Construcción de Filas HTML
        rows_html = []
        for _, row in pivot_table.iterrows():
            precios_validos = [
                row[t]
                for t in tiendas
                if row[t] != "-" and isinstance(row[t], (int, float))
            ]
            max_val = max(precios_validos) if precios_validos else 0
            min_val = min(precios_validos) if precios_validos else 0

            celdas = []
            for tienda in tiendas:
                val = row[tienda]
                es_num = isinstance(val, (int, float))
                es_max = es_num and val == max_val and max_val != min_val
                es_min = es_num and val == min_val and max_val != min_val

                # Lógica de colores Tailwind v4
                bg_class = (
                    "bg-emerald-50"
                    if es_max
                    else "bg-amber-50"
                    if es_min
                    else "bg-slate-50"
                    if val == "-"
                    else "bg-white"
                )
                dot_color = (
                    "bg-emerald-500"
                    if es_max
                    else "bg-red-500"
                    if es_min
                    else "border border-slate-300"
                )

                celdas.append(f"""
                    <td class="p-3 text-center border border-slate-200 {bg_class} min-w-[140px]">
                        <div class="flex flex-col items-center gap-1">
                            <div class="flex items-center gap-2">
                                <span class="h-2.5 w-2.5 rounded-full {dot_color}"></span>
                                <span class="text-sm {"font-bold text-slate-900" if es_max or es_min else "text-slate-600"}">
                                    {f"S/ {val:,.2f}" if es_num else val}
                                </span>
                            </div>
                            {crear_variacion_html(val, variaciones.get(row["nombre_producto"], {}).get(tienda))}
                        </div>
                    </td>
                """)

            rows_html.append(f"""
                <tr class="hover:bg-slate-50/50 transition-colors">
                    <td class="p-3 text-sm font-semibold text-slate-700 bg-white border border-slate-200 sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                        {row["nombre_producto"]}
                    </td>
                    {"".join(celdas)}
                </tr>
            """)

        # Header y Layout Final
        header_tiendas = "".join(
            [
                f'<th class="p-3 text-xs text-center font-bold uppercase text-slate-500 bg-slate-100 border border-slate-200">{t}</th>'
                for t in tiendas
            ]
        )

        return mo.Html(f"""
        <div class="w-full font-sans p-4 bg-white rounded-xl shadow-sm border border-slate-200">
            <div class="mb-6 text-center">
                <h3 class="text-xl font-bold text-blue-800 flex items-center justify-center gap-2">
                    <span class="text-2xl">📊</span> Comparativa de Precios
                    <span class="font-light text-blue-800">| {fecha_mas_reciente.strftime("%d/%m/%Y")}</span>
                </h3>
            </div>

            <div class="flex flex-wrap justify-center gap-x-8 gap-y-2 mb-6 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div class="flex items-center gap-4 text-xs font-medium text-slate-600">
                    <span class="flex items-center gap-1.5"><i class="h-3 w-3 rounded-full bg-emerald-500"></i> Más Caro</span>
                    <span class="flex items-center gap-1.5"><i class="h-3 w-3 rounded-full bg-red-500"></i> Más Barato</span>
                </div>
                <div class="h-4 w-px bg-slate-300 hidden sm:block"></div>
                <div class="flex items-center gap-4 text-xs font-medium text-slate-600">
                    <span>📈 <span class="text-emerald-600">Subió</span></span>
                    <span>📉 <span class="text-red-600">Bajó</span></span>
                    <span>➡️ <span class="text-slate-400">Sin cambios</span></span>
                </div>
            </div>

            <div class="relative overflow-auto border border-slate-200 rounded-lg shadow-inner" style="max-height: 500px;">
                <table class="w-full border-collapse text-left">
                    <thead>
                        <tr>
                            <th class="p-3 text-xs font-bold uppercase tracking-wider text-slate-500 bg-slate-100 border border-slate-200 sticky top-0 left-0 z-30">
                                Producto
                            </th>
                            {header_tiendas}
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-200">
                        {"".join(rows_html)}
                    </tbody>
                </table>
            </div>
        </div>
        """)
    return (render_comparativa_ecommerce,)


@app.cell
def _(
    apply_filters,
    custom_card,
    df,
    el_bulk,
    el_date_range,
    el_ecommerce,
    el_esp,
    el_marca,
    el_pres,
    el_prod_biom,
    el_products,
    el_sub,
    render_comparativa_ecommerce,
):
    df_comparativa = apply_filters(
        df,
        nombre_producto=el_products.value,
        subcategoria=el_sub.value,
        biomont=el_prod_biom.value,
        presentacion=el_pres.value,
        especie=el_esp.value,
        ecommerce=el_ecommerce.value,
        marca=el_marca.value,
        filtro_bulk=el_bulk.value,
        start_date=el_date_range.value[0],
        end_date=el_date_range.value[1],
        apply_ecommerce=False,
    )

    table_comparativa = render_comparativa_ecommerce(df_comparativa)
    card_comparativa = custom_card(
        title="🏪 Comparativa de Precios por E-commerce",
        content=table_comparativa,
        width="100%",
    )
    card_comparativa
    return


@app.cell
def _(go):
    # Mas graficos
    def get_boxplot(df_filtrado):
        fig_boxplot = go.Figure()

        for col, name, color in [
            ("maximo", "Máximo", "red"),
            ("minimo", "Mínimo", "green"),
            ("promedio", "Promedio", "blue"),
        ]:
            fig_boxplot.add_trace(
                go.Box(
                    y=df_filtrado[col].dropna(),
                    name=name,
                    marker_color=color,
                    boxmean=True,
                )
            )

        fig_boxplot.update_layout(
            title="Distribución de Precios",
            yaxis_title="Precio (S/)",
            template="plotly_white",
            height=300,
            showlegend=False,
        )

        return fig_boxplot
    return (get_boxplot,)


@app.cell
def _(custom_card, df_filtered, get_boxplot, mo):
    fig_2 = get_boxplot(df_filtered)
    boxplot_fig = mo.ui.plotly(fig_2)
    boxplot_card = custom_card(
        title="📉 Distribución de Precios", content=boxplot_fig, width="100%"
    )
    return (boxplot_card,)


@app.cell
def _(go):
    def get_counter_plot(df_filtrado):
        # Gráfico de conteo por día
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
                marker_color="orange",
            )
        )

        fig_conteo.update_layout(
            title="Número de productos por día",
            xaxis_title="Fecha",
            yaxis_title="Cantidad de productos",
            template="plotly_white",
            height=300,
        )
        return fig_conteo
    return (get_counter_plot,)


@app.cell
def _(custom_card, df_filtered, get_counter_plot, mo):
    fig_3 = get_counter_plot(df_filtered)
    counter_fig = mo.ui.plotly(fig_3)
    counter_card = custom_card(
        title="🔢 Conteo de SKUs por Día", content=counter_fig, width="100%"
    )
    return (counter_card,)


@app.cell
def _(boxplot_card, counter_card, mo):
    mo.hstack([boxplot_card, counter_card], widths=[1, 1], gap=2, align="start")
    return


@app.cell
def _(df_filtered):
    tabla_resumen = (
        df_filtered.groupby(
            ["descripcion_producto", "presentacion_producto", "ecommerce"]
        )
        .agg({"promedio": "mean", "maximo": "max", "minimo": "min"})
        .sort_values("promedio", ascending=False)
        .reset_index()
        .head(10)
    )
    return (tabla_resumen,)


@app.cell
def _(custom_card, mo, tabla_resumen):
    table = mo.ui.table(
        tabla_resumen,
        page_size=10,
        selection=None,
        show_data_types=False,
        format_mapping={
            "promedio": lambda x: f"S/ {x:.2f}",
            "maximo": lambda x: f"S/ {x:.2f}",
            "minimo": lambda x: f"S/ {x:.2f}",
        },
    )

    table_2 = mo.plain(tabla_resumen)

    card_table = custom_card(
        title="📋 Datos Detallados", content=table, width="100%"
    )
    card_table
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
