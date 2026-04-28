import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

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

    # --- CREACIÓN DE PESTAÑAS ---
    # Podés agregar más nombres a la lista para crear más pestañas en el futuro
    tab_ho, tab_graficos = st.tabs(["🛡️ Gestión de Hand Over y Garantías", "📈 Análisis Visual"])

    # ---------------------------------------------------------
    # PESTAÑA 1: GESTIÓN DE HAND OVER
    # ---------------------------------------------------------
    with tab_ho:
        st.header("Gestión de Hand Over y Garantías")
        
        # Procesamiento de datos para HO
        df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
        df["Fecha de Hand over"] = pd.to_datetime(df["Fecha de Hand over"], errors='coerce')
        df['TIENE_HO'] = df["Fecha de Hand over"].notna()
        df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
        col_ei = "ESTADO INTERNO"
        df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()

        # FILTROS SUPERIORES EN CASCADA
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

        # SIDEBAR (FILTROS FIJOS)
        st.sidebar.header("Filtros de Categoría")
        canales = sorted(df["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df.columns else []
        filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)
        vendedores = sorted(df["Vendedor"].dropna().unique()) if "Vendedor" in df.columns else []
        filtro_vendedor = st.sidebar.multiselect("Vendedor", options=vendedores)

        # LÓGICA DE FILTRADO FINAL
        df_f = df.copy()
        if mes_sel != "Todos":
            df_f = df_f[df_f["Mes_Display"] == mes_sel]
        if ei_sel != "Todos":
            df_f = df_f[df_f[col_ei] == ei_sel]
        if filtro_canal:
            df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
        if filtro_vendedor:
            df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

        # MÉTRICAS
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

        # TABLA
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
    # PESTAÑA 2: ANÁLISIS VISUAL (NUEVA)
    # ---------------------------------------------------------
    with tab_graficos:
        st.header("Análisis Visual de Gestión")
        
        if not fal_v.empty:
            g1, g2 = st.columns(2)
            
            with g1:
                st.write("### Pendientes por Vendedor")
                v_counts = fal_v["Vendedor"].value_counts().reset_index()
                v_counts.columns = ["Vendedor", "Cantidad"]
                fig_bar = px.bar(v_counts, x="Vendedor", y="Cantidad", color="Cantidad", template="plotly_white")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with g2:
                st.write("### Distribución de Estados Internos")
                fig_pie = px.pie(fal_v, names="ESTADO INTERNO", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.success("No hay datos pendientes para mostrar gráficos.")

except Exception as e:
    st.error("Error al cargar el portal por pestañas.")
    st.write(e)
