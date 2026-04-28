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
    # PESTAÑA 1: GESTIÓN DE HAND OVER
    # ---------------------------------------------------------
    with tab_ho:
        st.header("Gestión de Hand Over y Garantías")
        
        # Filtros en Cascada
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

        st.sidebar.header("Filtros de Categoría")
        canales = sorted(df["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df.columns else []
        filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)
        vendedores = sorted(df["Vendedor"].dropna().unique()) if "Vendedor" in df.columns else []
        filtro_vendedor = st.sidebar.multiselect("Vendedor", options=vendedores)

        df_f = df.copy()
        if mes_sel != "Todos": df_f = df_f[df_f["Mes_Display"] == mes_sel]
        if ei_sel != "Todos": df_f = df_f[df_f[col_ei] == ei_sel]
        if filtro_canal: df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
        if filtro_vendedor: df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        pat_v = df_f[df_f["Fecha de Patentamiento"].notna()]
        ent_v = df_f[df_f["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
        fal_v = pat_v[~pat_v['TIENE_HO']]
        
        c1.metric("Patentados", len(pat_v))
        c2.metric("Entregados", len(ent_v))
        c3.metric("Faltan Hand Over", len(fal_v), delta_color="inverse")
        eficacia = (len(pat_v[pat_v['TIENE_HO']]) / len(pat_v) * 100) if len(pat_v) > 0 else 0
        c4.metric("% Eficacia", f"{eficacia:.1f}%")

        st.subheader(f"📋 Listado: {mes_sel} | {ei_sel}")
        modo = st.radio("Filtro tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
        df_final = fal_v if modo == "Solo Pendientes ⚠️" else df_f
        
        busq = st.text_input("🔍 Búsqueda rápida:")
        if busq:
            mask = df_final.apply(lambda row: row.astype(str).str.contains(busq, case=False).any(), axis=1)
            df_final = df_final[mask]

        cols_ok = [c for c in COLUMNAS_HO if c in df_final.columns]
        st.dataframe(df_final[cols_ok], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: ANÁLISIS DE TIEMPOS Y VOLÚMENES (CON DÍAS HÁBILES)
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos y Volúmenes Operativos")
        
        v1, v2 = st.columns(2)
        v1.metric("Cantidad de Facturaciones", f"{df['Fecha de Facturacion'].notna().sum()} Unid.")
        v2.metric("Cantidad de Patentamientos", f"{df['Fecha de Patentamiento'].notna().sum()} Unid.")

        st.divider()
        st.subheader("📊 Evolución Mensual (Gráfico Interactivo)")
        st.info("💡 Hacé clic en una barra para filtrar las demoras y la tabla detallada.")
        
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            años = sorted(list(set(df["Fecha de Facturacion"].dt.year.dropna().unique()) | 
                               set(df["Fecha de Patentamiento"].dt.year.dropna().unique())), reverse=True)
            año_sel = st.selectbox("Seleccionar Año:", años if años else [2026], key="sel_año_t")
        with g_col2:
            tipo_g = st.pills("Evolución Mensual de:", ["Facturación", "Patentamiento"], default="Facturación", key="pill_tipo_t")

        # Ajuste de filtro para que la tabla sea coherente con lo seleccionado
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
        # Ahora df_t contiene a todos los del año o mes seleccionado por el botón de Facturación/Patentamiento
        df_t = df_g.copy() if mes_click else df_g.copy() # Cambiado de df.copy a df_g para respetar el filtro de volumen inicial
        if mes_click:
            df_t = df_t[df_t["Mes_Nom"] == mes_click]

        hoy_np = np.datetime64(datetime.now().date())

        def calc_working_days(start, end):
            if pd.isna(start): return None
            f_inicio = np.datetime64(start, 'D')
            f_final = np.datetime64(end, 'D') if pd.notna(end) else hoy_np
            if f_inicio > f_final: return 0
            return int(np.busday_count(f_inicio, f_final))

        df_t["Facturación a Gestor"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Facturacion"], r["Fecha que el Gestor Retira Doc"]), axis=1)
        df_t["Gestoría"] = df_t.apply(lambda r: calc_working_days(r["Fecha que el Gestor Retira Doc"], r["Fecha Disponibilidad Papeles"]), axis=1)
        df_t["Papeles a Entrega"] = df_t.apply(lambda r: calc_working_days(r["Fecha Disponibilidad Papeles"], r["Fecha de confirmacion de entrega"]), axis=1)
        df_t["Demora Total"] = df_t.apply(lambda r: calc_working_days(r["Fecha de Facturacion"], r["Fecha de confirmacion de entrega"]), axis=1)

        # --- MÉTRICAS CON OBJETIVOS Y AYUDA ---
        st.divider()
        st.subheader(f"⏳ Promedios Días Hábiles - {mes_click if mes_click else 'Anual'}")
        mt1, mt2, mt3, mt4 = st.columns(4)
        
        OBJ1, OBJ2, OBJ3 = 2, 3, 3
        p1, p2, p3, p4 = df_t["Facturación a Gestor"].mean(), df_t["Gestoría"].mean(), df_t["Papeles a Entrega"].mean(), df_t["Demora Total"].mean()

        mt1.metric("Fact. a Gestor", f"{p1:.1f} d" if pd.notna(p1) else "0.0 d", 
                   delta=f"{p1-OBJ1:.1f} vs Obj" if pd.notna(p1) else None, delta_color="inverse",
                   help=f"Objetivo: {OBJ1} días hábiles.")
        
        mt2.metric("Gestión Gestor", f"{p2:.1f} d" if pd.notna(p2) else "0.0 d", 
                   delta=f"{p2-OBJ2:.1f} vs Obj" if pd.notna(p2) else None, delta_color="inverse",
                   help=f"Objetivo: {OBJ2} días hábiles.")
        
        mt3.metric("Papeles a Entrega", f"{p3:.1f} d" if pd.notna(p3) else "0.0 d", 
                   delta=f"{p3-OBJ3:.1f} vs Obj" if pd.notna(p3) else None, delta_color="inverse",
                   help=f"Objetivo: {OBJ3} días hábiles.")
        
        mt4.metric("Ciclo Total", f"{p4:.1f} d" if pd.notna(p4) else "0.0 d", 
                   help="Suma total de días hábiles desde Facturación.")

        st.subheader(f"📋 Detalle de Unidades ({tipo_g} en el periodo)")
        cols_t_view = ["Vendedor", "Cliente", "Chasis", "Facturación a Gestor", "Gestoría", "Papeles a Entrega", "Demora Total", "Estado"]
        st.dataframe(df_t[cols_t_view], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 3: ANÁLISIS VISUAL
    # ---------------------------------------------------------
    with tab_graficos:
        st.header("Análisis Visual de Gestión")
        if 'fal_v' in locals() and not fal_v.empty:
            g1, g2 = st.columns(2)
            with g1:
                st.write("### Pendientes de HO por Vendedor")
                v_counts = fal_v["Vendedor"].value_counts().reset_index()
                v_counts.columns = ["Vendedor", "Cant"]
                st.plotly_chart(px.bar(v_counts, x="Vendedor", y="Cant", color="Cant", template="plotly_white"), use_container_width=True)
            with g2:
                st.write("### Estado Interno de los Pendientes")
                st.plotly_chart(px.pie(fal_v, names="ESTADO INTERNO", hole=0.4), use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar el portal: {e}")
