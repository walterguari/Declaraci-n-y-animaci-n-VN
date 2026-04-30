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
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado", "Fecha de confirmacion de entrega", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    # --- CARGA DE DATOS ---
    df_raw = conn.read(spreadsheet=url_base)
    df_base = df_raw.dropna(how='all')
    df_base.columns = [str(c).strip() for c in df_base.columns]

    # --- SIDEBAR ---
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
        "Fecha de confirmacion de entrega",
        "Fecha de Pedido de Preparacion"  # <--- NUEVA COLUMNA AGREGADA
    ]
    for c in cols_a_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    # Auxiliares globales
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
    # PESTAÑA 1: GESTIÓN DE HAND OVER (Sin cambios)
    # ---------------------------------------------------------
    with tab_ho:
        st.header("Gestión de Hand Over y Garantías")
        st.write("### 📅 1. Seleccioná el Mes con Pendientes")
        meses_pendientes = df[~df['TIENE_HO']].dropna(subset=["Fecha de Patentamiento"]).sort_values("Fecha de Patentamiento")
        opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()
        mes_sel = st.pills("Meses detectados:", ["Todos"] + opciones_meses, default="Todos", key="p_mes")

        st.write("### 🏷️ 2. Filtrar por Estado Interno (Solo pendientes)")
        df_temp_ei = df[~df['TIENE_HO']].copy()
        if mes_sel != "Todos":
            df_temp_ei = df_temp_ei[df_temp_ei["Mes_Display"] == mes_sel]
        
        est_disponibles = sorted([e for e in df_temp_ei[col_ei].unique() if e.upper() not in ["NAN", "", "NONE"]])
        ei_sel = st.pills("Categorías con pendientes:", ["Todos"] + est_disponibles, default="Todos", key="p_ei")

        df_f_ho = df.copy()
        if mes_sel != "Todos": df_f_ho = df_f_ho[df_f_ho["Mes_Display"] == mes_sel]
        if ei_sel != "Todos": df_f_ho = df_f_ho[df_f_ho[col_ei] == ei_sel]

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        pat_v = df_f_ho[df_f_ho["Fecha de Patentamiento"].notna()]
        ent_v = df_f_ho[df_f_ho["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
        fal_v = pat_v[~pat_v['TIENE_HO']]
        
        c1.metric("Patentados", len(pat_v))
        c2.metric("Entregados", len(ent_v))
        c3.metric("Faltan Hand Over", len(fal_v), delta_color="inverse")
        eficacia = (len(pat_v[pat_v['TIENE_HO']]) / len(pat_v) * 100) if len(pat_v) > 0 else 0
        c4.metric("% Eficacia", f"{eficacia:.1f}%")

        modo = st.radio("Filtro tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
        df_final = fal_v if modo == "Solo Pendientes ⚠️" else df_f_ho
        
        busq = st.text_input("🔍 Búsqueda rápida:")
        if busq:
            mask = df_final.apply(lambda row: row.astype(str).str.contains(busq, case=False).any(), axis=1)
            df_final = df_final[mask]

        cols_ok = [c for c in COLUMNAS_HO if c in df_final.columns]
        st.dataframe(df_final[cols_ok], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: ANÁLISIS DE TIEMPOS (Ajustada según imagen)
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos Operativos (Días Hábiles)")
        
        v1, v2 = st.columns(2)
        v1.metric("Cantidad de Facturaciones", f"{df['Fecha de Facturacion'].notna().sum()} Unid.")
        v2.metric("Cantidad de Patentamientos", f"{df['Fecha de Patentamiento'].notna().sum()} Unid.")

        st.divider()
        st.subheader("📊 Evolución Mensual e Interactividad")
        st.info("💡 Hacé clic en una barra para filtrar las demoras y la tabla detallada.")
        
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
            
            fig_v = px.bar(resumen.sort_values("Mes_Num"), x="Mes_Nom", y="Cant", text_auto=True, 
                           title=f"Volumen de {tipo_g} - {año_sel}", 
                           color_discrete_sequence=['#3498db' if tipo_g == "Facturación" else '#2ecc71'],
                           template="plotly_white")
            
            evento_clic = st.plotly_chart(fig_v, use_container_width=True, on_select="rerun")
            
            if evento_clic and "selection" in evento_clic and evento_clic["selection"]["points"]:
                mes_click = evento_clic["selection"]["points"][0]["x"]
                st.success(f"🔎 Auditando {tipo_g}: **{mes_click} {año_sel}**")

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

        # --- CÁLCULOS DE TIEMPOS (Ajuste solicitado) ---
        df_t["Facturación a Gestor"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Facturacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        df_t["Prep a Retiro"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Pedido de Preparacion"], r["Fecha que el Gestor Retira Doc"]), axis=1) # <--- NUEVO
        df_t["Gestoría"] = df_t.apply(lambda r: calc_working_days(r["Fecha que el Gestor Retira Doc"], r["Fecha Disponibilidad Papeles"]), axis=1)
        df_t["Papeles a Entrega"] = df_t.apply(lambda r: calc_working_days(r["Fecha Disponibilidad Papeles"], r["Fecha de confirmacion de entrega"]), axis=1)
        df_t["Demora Total"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Facturacion"], r["Fecha de confirmacion de entrega"]), axis=1)

        st.divider()
        st.subheader(f"⏳ Promedios Días Hábiles - {mes_click if mes_click else 'Anual'}")
        
        # AJUSTE DE COLUMNAS PARA EL NUEVO INDICADOR (5 columnas en lugar de 4)
        mt1, mt_prep, mt2, mt3, mt4 = st.columns(5)
        
        OBJ1, OBJ_PREP, OBJ2, OBJ3 = 2, 1, 3, 3 # Agregué un objetivo estimado para Prep de 1 día
        p1, p_prep, p2, p3, p4 = df_t["Facturación a Gestor"].mean(), df_t["Prep a Retiro"].mean(), df_t["Gestoría"].mean(), df_t["Papeles a Entrega"].mean(), df_t["Demora Total"].mean()

        mt1.metric("Fact. a Gestor", f"{p1:.1f} d" if pd.notna(p1) else "0.0 d", 
                   delta=f"{p1-OBJ1:.1f} vs Obj" if pd.notna(p1) else None, delta_color="inverse",
                   help="Mide: Fecha Retiro Gestor - Fecha Facturación.")
        
        # --- NUEVO INDICADOR SOLICITADO ---
        mt_prep.metric("Prep. a Retiro", f"{p_prep:.1f} d" if pd.notna(p_prep) else "0.0 d", 
                   delta=f"{p_prep-OBJ_PREP:.1f} vs Obj" if pd.notna(p_prep) else None, delta_color="inverse",
                   help="Mide: Fecha Retiro Gestor - Fecha de Pedido de Preparación.")
        
        mt2.metric("Gestión Gestor", f"{p2:.1f} d" if pd.notna(p2) else "0.0 d", 
                   delta=f"{p2-OBJ2:.1f} vs Obj" if pd.notna(p2) else None, delta_color="inverse",
                   help="Objetivo: {OBJ2} días. Mide: Fecha Disp. Papeles - Fecha Retiro Gestor.")
        
        mt3.metric("Papeles a Entrega", f"{p3:.1f} d" if pd.notna(p3) else "0.0 d", 
                   delta=f"{p3-OBJ3:.1f} vs Obj" if pd.notna(p3) else None, delta_color="inverse",
                   help="Objetivo: {OBJ3} días. Mide: Fecha Conf. Entrega - Fecha Disp. Papeles.")
        
        mt4.metric("Ciclo Total", f"{p4:.1f} d" if pd.notna(p4) else "0.0 d", 
                   help="Mide: Fecha Conf. Entrega - Fecha Facturación (Ciclo Completo).")

        st.subheader(f"📋 Detalle de Unidades ({tipo_g} en el periodo)")
        
        # --- CONFIGURACIÓN DE LA TABLA (Añadiendo el nuevo cálculo) ---
        st.dataframe(
            df_t[["Marca", "Vendedor", "Cliente", "Chasis", "Prep a Retiro", "Facturación a Gestor", "Gestoría", "Papeles a Entrega", "Demora Total", "Fecha de confirmacion de entrega", "Estado"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Prep a Retiro": st.column_config.NumberColumn(help="Cálculo: [Fecha que el Gestor Retira Doc] - [Fecha de Pedido de Preparacion]"),
                "Facturación a Gestor": st.column_config.NumberColumn(help="Cálculo: [Fecha que el Gestor Retira Doc] - [Fecha de Facturación]"),
                "Gestoría": st.column_config.NumberColumn(help="Cálculo: [Fecha Disponibilidad Papeles] - [Fecha que el Gestor Retira Doc]"),
                "Papeles a Entrega": st.column_config.NumberColumn(help="Cálculo: [Fecha de confirmacion de entrega] - [Fecha Disponibilidad Papeles]"),
                "Demora Total": st.column_config.NumberColumn(help="Cálculo: [Fecha de confirmacion de entrega] - [Fecha de Facturación]"),
                "Fecha de confirmacion de entrega": st.column_config.DateColumn("Fecha Entrega")
            }
        )

    # ---------------------------------------------------------
    # PESTAÑA 3: ANÁLISIS VISUAL
    # ---------------------------------------------------------
    with tab_graficos:
        st.header("Análisis Visual de Gestión")
        if not df.empty:
            g1, g2 = st.columns(2)
            with g1:
                st.write("### Unidades por Marca")
                st.plotly_chart(px.bar(df["Marca"].value_counts().reset_index(), x="Marca", y="count", color="Marca", template="plotly_white"), use_container_width=True)
            with g2:
                st.write("### Estado Interno de los Pendientes")
                st.plotly_chart(px.pie(df[df['TIENE_HO']==False], names="ESTADO INTERNO", hole=0.4), use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar el portal: {e}")
