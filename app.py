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

# Columnas para la pestaña de Hand Over
COLUMNAS_HO = [
    "Marca", "Vendedor", "Cliente", "Teléfono", 
    "Chasis", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Estado", "Fecha de confirmacion de entrega", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    # --- CARGA DE DATOS ---
    df_raw = conn.read(spreadsheet=url_base)
    df_base = df_raw.dropna(how='all')
    df_base.columns = [str(c).strip() for c in df_base.columns]

    # --- SIDEBAR (FILTROS GLOBAL: MARCA SÍ, VENDEDOR NO) ---
    st.sidebar.header("Filtros Globales")
    
    marcas = sorted(df_base["Marca"].dropna().unique()) if "Marca" in df_base.columns else []
    filtro_marca = st.sidebar.multiselect("Seleccionar Marca", options=marcas)

    canales = sorted(df_base["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df_base.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)

    # --- APLICACIÓN DEL FILTRO GLOBAL ---
    df = df_base.copy()
    if filtro_marca:
        df = df[df["Marca"].isin(filtro_marca)]
    if filtro_canal:
        df = df[df["Canal de Venta"].isin(filtro_canal)]

    # --- PROCESAMIENTO GLOBAL DE FECHAS ---
    cols_a_fecha = [
        "Fecha de Patentamiento", "Fecha de Hand over", "Fecha de Facturacion",
        "Fecha que el Gestor Retira Doc", "Fecha Disponibilidad Papeles",
        "Fecha de confirmacion de entrega"
    ]
    for c in cols_a_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    # Auxiliares globales
    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    df["ESTADO INTERNO"] = df["ESTADO INTERNO"].fillna("SIN ESTADO").astype(str).str.strip()

    tab_ho, tab_tiempos, tab_graficos = st.tabs([
        "🛡️ Gestión de Hand Over y Garantías", 
        "⏱️ Análisis de Tiempos", 
        "📈 Análisis Visual"
    ])

    # ---------------------------------------------------------
    # PESTAÑA 2: ANÁLISIS DE TIEMPOS
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos Operativos (Días Hábiles)")
        
        # Selectores
        g_col1, g_col2 = st.columns(2)
        años = sorted(list(set(df["Fecha de Facturacion"].dt.year.dropna().unique()) | set(df["Fecha de Patentamiento"].dt.year.dropna().unique())), reverse=True)
        año_sel = g_col1.selectbox("Año:", años if años else [2026], key="sel_año_t")
        tipo_g = g_col2.pills("Evolución Mensual de:", ["Facturación", "Patentamiento"], default="Facturación", key="pill_tipo_t")

        col_f = "Fecha de Facturacion" if tipo_g == "Facturación" else "Fecha de Patentamiento"
        df_g = df[df[col_f].dt.year == año_sel].copy()
        
        mes_click = None
        if not df_g.empty:
            df_g["Mes_Num"] = df_g[col_f].dt.month
            df_g["Mes_Nom"] = df_g[col_f].dt.strftime('%B')
            resumen = df_g.groupby(["Mes_Num", "Mes_Nom"]).size().reset_index(name="Cant")
            fig_v = px.bar(resumen.sort_values("Mes_Num"), x="Mes_Nom", y="Cant", text_auto=True, color_discrete_sequence=['#3498db'], template="plotly_white")
            evento_clic = st.plotly_chart(fig_v, use_container_width=True, on_select="rerun")
            if evento_clic and "selection" in evento_clic and evento_clic["selection"]["points"]:
                mes_click = evento_clic["selection"]["points"][0]["x"]

        # --- LÓGICA DE DÍAS HÁBILES ---
        df_t = df_g.copy()
        if mes_click:
            df_t = df_t[df_t["Mes_Nom"] == mes_click]

        hoy_np = np.datetime64(datetime.now().date())

        def calc_working_days(start, end):
            if pd.isna(start): return None
            f_inicio = np.datetime64(start, 'D')
            f_final = np.datetime64(end, 'D') if pd.notna(end) else hoy_np
            if f_inicio > f_final: return 0
            dias = int(np.busday_count(f_inicio, f_final))
            return dias if dias < 365 else None

        # Función auxiliar para formatear rango de fechas
        def get_range(start, end):
            if pd.isna(start): return "Falta Fecha"
            s = start.strftime('%d/%m')
            e = end.strftime('%d/%m') if pd.notna(end) else "Hoy"
            return f"({s} al {e})"

        # Cálculos de días y textos de auditoría
        df_t["Facturación a Gestor"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Facturacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        df_t["Fechas Fact."] = df_t.apply(lambda r: get_range(r["Fecha de Facturacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        
        df_t["Gestoría"] = df_t.apply(lambda r: calc_working_days(r["Fecha que el Gestor Retira Doc"], r["Fecha Disponibilidad Papeles"]), axis=1)
        df_t["Fechas Gest."] = df_t.apply(lambda r: get_range(r["Fecha que el Gestor Retira Doc"], r["Fecha Disponibilidad Papeles"]), axis=1)
        
        df_t["Papeles a Entrega"] = df_t.apply(lambda r: calc_working_days(r["Fecha Disponibilidad Papeles"], r["Fecha de confirmacion de entrega"]), axis=1)
        df_t["Fechas Entrega"] = df_t.apply(lambda r: get_range(r["Fecha Disponibilidad Papeles"], r["Fecha de confirmacion de entrega"]), axis=1)
        
        df_t["Demora Total"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Facturacion"], r["Fecha de confirmacion de entrega"]), axis=1)

        # MÉTRICAS
        st.divider()
        st.subheader(f"⏳ Promedios Días Hábiles - {mes_click if mes_click else 'Anual'}")
        mt1, mt2, mt3, mt4 = st.columns(4)
        p1, p2, p3, p4 = df_t["Facturación a Gestor"].mean(), df_t["Gestoría"].mean(), df_t["Papeles a Entrega"].mean(), df_t["Demora Total"].mean()
        
        mt1.metric("Fact. a Gestor", f"{p1:.1f} d" if pd.notna(p1) else "0.0 d", delta=f"{p1-2:.1f} vs Obj" if pd.notna(p1) else None, delta_color="inverse")
        mt2.metric("Gestión Gestor", f"{p2:.1f} d" if pd.notna(p2) else "0.0 d", delta=f"{p2-3:.1f} vs Obj" if pd.notna(p2) else None, delta_color="inverse")
        mt3.metric("Papeles a Entrega", f"{p3:.1f} d" if pd.notna(p3) else "0.0 d", delta=f"{p3-3:.1f} vs Obj" if pd.notna(p3) else None, delta_color="inverse")
        mt4.metric("Ciclo Total", f"{p4:.1f} d" if pd.notna(p4) else "0.0 d")

        st.subheader(f"📋 Detalle de Unidades ({tipo_g} en el periodo)")
        
        # TABLA CON COLUMNAS DE FECHAS DE AUDITORÍA
        st.dataframe(
            df_t[["Marca", "Vendedor", "Cliente", "Chasis", "Facturación a Gestor", "Fechas Fact.", "Gestoría", "Fechas Gest.", "Papeles a Entrega", "Fechas Entrega", "Demora Total", "Fecha de confirmacion de entrega", "Estado"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Fechas Fact.": st.column_config.TextColumn("Rango Facturación", width="small"),
                "Fechas Gest.": st.column_config.TextColumn("Rango Gestoría", width="small"),
                "Fechas Entrega": st.column_config.TextColumn("Rango Entrega", width="small"),
                "Fecha de confirmacion de entrega": st.column_config.DateColumn("Fecha Entrega Real")
            }
        )

    # ---------------------------------------------------------
    # PESTAÑA 1 y 3 (HO y Visual) mantenidas según el flujo previo
    # ---------------------------------------------------------

except Exception as e:
    st.error(f"Error al cargar el portal: {e}")
