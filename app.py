import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Portal de Gestión VN", layout="wide", page_icon="🚗")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

COLUMNAS_HO = [
    "Marca", "Vendedor", "Cliente", "Teléfono", 
    "Chasis", "VIN", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado", "Fecha de confirmacion de entrega", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    # --- CARGA DE DATOS ---
    df_raw = conn.read(spreadsheet=url_base)
    df_base = df_raw.dropna(how='all')
    df_base.columns = [str(c).strip() for c in df_base.columns]

    # --- FILTROS SIDEBAR ---
    st.sidebar.header("Filtros Globales")
    marcas = sorted(df_base["Marca"].dropna().unique()) if "Marca" in df_base.columns else []
    filtro_marca = st.sidebar.multiselect("Seleccionar Marca", options=marcas)

    canales = sorted(df_base["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df_base.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)

    df = df_base.copy()
    if filtro_marca: df = df[df["Marca"].isin(filtro_marca)]
    if filtro_canal: df = df[df["Canal de Venta"].isin(filtro_canal)]

    # --- PROCESAMIENTO DE FECHAS ---
    cols_a_fecha = [
        "Fecha de Patentamiento", "Fecha de Hand over", "Fecha de Facturacion",
        "Fecha que el Gestor Retira Doc", "Fecha Disponibilidad Papeles",
        "Fecha de confirmacion de entrega", "Fecha de Pedido de Preparacion" 
    ]
    for c in cols_a_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    col_ei = "ESTADO INTERNO"
    df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()

    # --- PESTAÑAS ---
    tab_ho, tab_tiempos, tab_graficos = st.tabs([
        "🛡️ Gestión de Hand Over", "⏱️ Análisis de Tiempos", "📈 Análisis Visual"
    ])

    # ---------------------------------------------------------
    # PESTAÑA 1: GESTIÓN DE HAND OVER
    # ---------------------------------------------------------
    with tab_ho:
        st.header("Gestión de Hand Over y Garantías")
        
        # Filtros de navegación
        st.write("### 📅 1. Seleccioná el Mes con Pendientes")
        meses_p = df[df["Fecha de Patentamiento"].notna()].sort_values("Fecha de Patentamiento")
        opciones_meses = meses_p["Mes_Display"].unique().tolist()
        mes_sel = st.pills("Meses detectados:", ["Todos"] + opciones_meses, default="Todos", key="p_mes")

        st.write("### 🏷️ 2. Filtrar por Estado Interno")
        df_temp_ei = df.copy()
        if mes_sel != "Todos": df_temp_ei = df_temp_ei[df_temp_ei["Mes_Display"] == mes_sel]
        est_disponibles = sorted([e for e in df_temp_ei[col_ei].unique() if e.upper() not in ["NAN", "", "NONE"]])
        ei_sel = st.pills("Categorías:", ["Todos"] + est_disponibles, default="Todos", key="p_ei")

        df_f_ho = df.copy()
        if mes_sel != "Todos": df_f_ho = df_f_ho[df_f_ho["Mes_Display"] == mes_sel]
        if ei_sel != "Todos": df_f_ho = df_f_ho[df_f_ho[col_ei] == ei_sel]

        st.divider()
        
        # --- LÓGICA DE MÉTRICAS SOLICITADA ---
        pat_v = df_f_ho[df_f_ho["Fecha de Patentamiento"].notna()]
        ent_v = pat_v[pat_v["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
        
        # El faltante es la resta directa entre patentados y entregados
        cantidad_faltante = len(pat_v) - len(ent_v)
        eficacia = (len(ent_v) / len(pat_v) * 100) if len(pat_v) > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Patentados", len(pat_v))
        c2.metric("Entregados", len(ent_v))
        c3.metric("Faltan Entregar", cantidad_faltante, delta_color="inverse")
        c4.metric("% Eficacia Entrega", f"{eficacia:.1f}%")

        # Tabla de datos
        modo = st.radio("Filtro tabla:", ["Solo Pendientes de Entrega ⚠️", "Todos"], horizontal=True)
        # Para la tabla "Solo pendientes" usamos los que no están entregados
        df_final = pat_v[~pat_v["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)] if modo == "Solo Pendientes de Entrega ⚠️" else df_f_ho
        
        busq = st.text_input("🔍 Búsqueda rápida (Cliente, Chasis, Patente...):")
        if busq:
            mask = df_final.apply(lambda row: row.astype(str).str.contains(busq, case=False).any(), axis=1)
            df_final = df_final[mask]

        cols_ok = [c for c in COLUMNAS_HO if c in df_final.columns]
        st.dataframe(df_final[cols_ok], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: ANÁLISIS DE TIEMPOS
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos Operativos")
        
        # Gráfico interactivo y selección de año
        g_col1, g_col2 = st.columns(2)
        años = sorted(list(set(df["Fecha de Facturacion"].dt.year.dropna().unique()) | set(df["Fecha de Patentamiento"].dt.year.dropna().unique())), reverse=True)
        año_sel = g_col1.selectbox("Año:", años if años else [2026], key="sel_año_t")
        tipo_g = g_col2.pills("Ver evolución de:", ["Facturación", "Patentamiento"], default="Facturación", key="pill_tipo_t")

        col_f = "Fecha de Facturacion" if tipo_g == "Facturación" else "Fecha de Patentamiento"
        df_g = df[df[col_f].dt.year == año_sel].copy()
        
        mes_click = None
        if not df_g.empty:
            df_g["Mes_Num"] = df_g[col_f].dt.month
            df_g["Mes_Nom"] = df_g[col_f].dt.strftime('%B')
            resumen = df_g.groupby(["Mes_Num", "Mes_Nom"]).size().reset_index(name="Cant")
            fig_v = px.bar(resumen.sort_values("Mes_Num"), x="Mes_Nom", y="Cant", text_auto=True, template="plotly_white", color_discrete_sequence=['#3498db'])
            evento_clic = st.plotly_chart(fig_v, use_container_width=True, on_select="rerun")
            if evento_clic and "selection" in evento_clic and evento_clic["selection"]["points"]:
                mes_click = evento_clic["selection"]["points"][0]["x"]

        # Cálculos de tiempos
        df_t = df_g.copy()
        if mes_click: df_t = df_t[df_t["Mes_Nom"] == mes_click]

        hoy = np.datetime64(datetime.now().date())
        def bus_days(s, e):
            if pd.isna(s): return None
            start, end = np.datetime64(s, 'D'), np.datetime64(e, 'D') if pd.notna(e) else hoy
            return int(np.busday_count(start, end)) if start <= end else 0

        df_t["Fact. a Gestor"] = df_t.apply(lambda r: bus_days(r["Fecha de Facturacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        df_t["Prep a Retiro"] = df_t.apply(lambda r: bus_days(r["Fecha de Pedido de Preparacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        df_t["Gestoría"] = df_t.apply(lambda r: bus_days(r["Fecha que el Gestor Retira Doc"], r["Fecha Disponibilidad Papeles"]), axis=1)
        df_t["Papeles a Entrega"] = df_t.apply(lambda r: bus_days(r["Fecha Disponibilidad Papeles"], r["Fecha de confirmacion de entrega"]), axis=1)
        df_t["Total"] = df_t.apply(lambda r: bus_days(r["Fecha de Facturacion"], r["Fecha de confirmacion de entrega"]), axis=1)

        # Métricas de tiempo
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Fact a Gestor", f"{df_t['Fact. a Gestor'].mean():.1f} d")
        m2.metric("Prep a Retiro", f"{df_t['Prep a Retiro'].mean():.1f} d")
        m3.metric("Gestoría", f"{df_t['Gestoría'].mean():.1f} d")
        m4.metric("Papeles a Ent.", f"{df_t['Papeles a Entrega'].mean():.1f} d")
        m5.metric("Ciclo Total", f"{df_t['Total'].mean():.1f} d")

        st.dataframe(df_t[["Marca", "Vendedor", "Cliente", "Chasis", "Fact. a Gestor", "Prep a Retiro", "Gestoría", "Papeles a Entrega", "Total", "Estado"]], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 3: ANÁLISIS VISUAL
    # ---------------------------------------------------------
    with tab_graficos:
        st.header("Análisis Visual")
        c_v1, c_v2 = st.columns(2)
        c_v1.plotly_chart(px.bar(df["Marca"].value_counts().reset_index(), x="Marca", y="count", title="Unidades por Marca"), use_container_width=True)
        c_v2.plotly_chart(px.pie(df[df['TIENE_HO']==False], names="ESTADO INTERNO", title="Distribución de Pendientes"), use_container_width=True)

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
