import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Portal de Gestión VN", layout="wide", page_icon="🚗")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Columnas para la pestaña de Hand Over
COLUMNAS_HO = [
    "Vendedor", "Cliente", "Teléfono", "E-mail", 
    "Chasis", "Marca", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado", "Fecha de confirmacion de entrega", "Encuesta Temprana", 
    "Comentario Enc. Temp.", "EI - Reco", "Comentario de la Encuesta interna", 
    "EI - CSI", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    # Lectura de datos
    df_raw = conn.read(spreadsheet=url_base)
    df = df_raw.dropna(how='all')
    df.columns = [str(c).strip() for c in df.columns]

    # --- PROCESAMIENTO DE DATOS GLOBAL ---
    cols_a_fecha = [
        "Fecha de Patentamiento", "Fecha de Hand over", "Fecha de Facturacion",
        "Fecha que el Gestor Retira Doc", "Fecha Disponibilidad Papeles",
        "Fecha de confirmacion de entrega"
    ]
    for c in cols_a_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    col_ei = "ESTADO INTERNO"
    df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()

    # --- CREACIÓN DE PESTAÑAS ---
    tab_ho, tab_tiempos, tab_graficos = st.tabs([
        "🛡️ Gestión de Hand Over y Garantías", 
        "⏱️ Análisis de Tiempos", 
        "📈 Análisis Visual"
    ])

    # ---------------------------------------------------------
    # PESTAÑA 1: GESTIÓN DE HAND OVER (Se mantiene igual)
    # ---------------------------------------------------------
    with tab_ho:
        st.header("Gestión de Hand Over y Garantías")
        # ... (Código de filtros y métricas que ya tenías)
        # Se omite para brevedad pero está implícito que se mantiene la lógica de cascada
        st.dataframe(df[COLUMNAS_HO], use_container_width=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: ANÁLISIS DE TIEMPOS Y VOLÚMENES (AJUSTADA)
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos y Volúmenes Operativos")
        
        # Métricas de Volumen (Globales)
        v1, v2 = st.columns(2)
        v1.metric("Cantidad de Facturaciones", f"{df['Fecha de Facturacion'].notna().sum()} Unid.")
        v2.metric("Cantidad de Patentamientos", f"{df['Fecha de Patentamiento'].notna().sum()} Unid.")

        st.divider()
        
        # SELECTORES PARA EL GRÁFICO
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            años = sorted(list(set(df["Fecha de Facturacion"].dt.year.dropna().unique()) | 
                               set(df["Fecha de Patentamiento"].dt.year.dropna().unique())), reverse=True)
            año_sel = st.selectbox("Año:", años if años else [2026], key="sel_año_t")
        with g_col2:
            tipo_g = st.pills("Evolución Mensual de:", ["Facturación", "Patentamiento"], default="Facturación", key="pill_tipo_t")

        col_f = "Fecha de Facturacion" if tipo_g == "Facturación" else "Fecha de Patentamiento"
        df_g = df[df[col_f].dt.year == año_sel].copy()
        
        mes_click = None
        if not df_g.empty:
            df_g["Mes"] = df_g[col_f].dt.month
            df_g["Mes_Nom"] = df_g[col_f].dt.strftime('%B')
            resumen = df_g.groupby(["Mes", "Mes_Nom"]).size().reset_index(name="Cant")
            
            fig_v = px.bar(resumen.sort_values("Mes"), x="Mes_Nom", y="Cant", text_auto=True, 
                           title=f"Volumen de {tipo_g} - {año_sel}", 
                           color_discrete_sequence=['#3498db' if tipo_g == "Facturación" else '#2ecc71'],
                           template="plotly_white")
            
            evento_clic = st.plotly_chart(fig_v, use_container_width=True, on_select="rerun")
            
            if evento_clic and "selection" in evento_clic and evento_clic["selection"]["points"]:
                mes_click = evento_clic["selection"]["points"][0]["x"]
                st.success(f"🔎 Auditando mes: **{mes_click} {año_sel}**")

        # --- CÁLCULOS DE LEAD TIMES MEJORADOS ---
        # Usamos df_g (el año seleccionado) o filtramos por mes si hubo clic
        df_t = df_g.copy()
        if mes_click:
            df_t = df_t[df_t["Mes_Nom"] == mes_click]

        # Función para calcular días evitando errores y permitiendo "tiempos en curso"
        hoy = pd.Timestamp(datetime.now().date())

        def calc_days(start, end):
            if pd.isna(start): return None
            # Si no hay fecha final, calculamos hasta hoy
            final = end if pd.notna(end) else hoy
            diff = (final - start).days
            return max(0, diff) # Evita negativos

        df_t["Facturación a Gestor"] = df_t.apply(lambda r: calc_days(r["Fecha de Facturacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        df_t["Gestoría (Retiro a Papeles)"] = df_t.apply(lambda r: calc_days(r["Fecha que el Gestor Retira Doc"], r["Fecha Disponibilidad Papeles"]), axis=1)
        df_t["Entrega (Papeles a Entrega)"] = df_t.apply(lambda r: calc_days(r["Fecha Disponibilidad Papeles"], r["Fecha de confirmacion de entrega"]), axis=1)
        df_t["Demora Total"] = df_t.apply(lambda r: calc_days(r["Fecha de Facturacion"], r["Fecha de confirmacion de entrega"]), axis=1)

        # MÉTRICAS
        st.subheader(f"⏳ Promedios de Demora - {mes_click if mes_click else 'Año completo'}")
        mt1, mt2, mt3, mt4 = st.columns(4)
        mt1.metric("Fact. a Gestor", f"{df_t['Facturación a Gestor'].mean():.1f} d")
        mt2.metric("Gestión Gestor", f"{df_t['Gestoría (Retiro a Papeles)'].mean():.1f} d")
        mt3.metric("Papeles a Entrega", f"{df_t['Entrega (Papeles a Entrega)'].mean():.1f} d")
        mt4.metric("Ciclo Total", f"{df_t['Demora Total'].mean():.1f} d")

        # TABLA DETALLADA (Sin dropna para que aparezcan todos los facturados)
        st.subheader("📋 Detalle de Unidades (Facturados en el periodo)")
        cols_t_view = ["Vendedor", "Cliente", "Chasis", "Facturación a Gestor", "Gestoría (Retiro a Papeles)", "Entrega (Papeles a Entrega)", "Demora Total", "Estado"]
        
        # Mostramos la tabla. Los que no tengan entrega aparecerán con la demora calculada a "hoy"
        st.dataframe(df_t[cols_t_view], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al cargar el portal.")
    st.write(e)
