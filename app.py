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
    # PESTAÑA 2: ANÁLISIS DE TIEMPOS
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos (Lead Times)")
        
        # Columnas necesarias para esta pestaña
        cols_fechas = [
            "Fecha de Facturacion", "Fecha de Pedido de Preparacion", 
            "Fecha que el Gestor Retira Doc", "Fecha de Patentamiento", 
            "Fecha Disponibilidad Papeles", "Fecha Arribo", 
            "Fecha de confirmacion de entrega"
        ]
        
        df_t = df.copy()
        for col in cols_fechas:
            if col in df_t.columns:
                df_t[col] = pd.to_datetime(df_t[col], errors='coerce')

        # Cálculos de días
        df_t["Días Logística (Pedido-Arribo)"] = (df_t["Fecha Arribo"] - df_t["Fecha de Pedido de Preparacion"]).dt.days
        df_t["Días Patentamiento"] = (df_t["Fecha de Patentamiento"] - df_t["Fecha que el Gestor Retira Doc"]).dt.days
        df_t["Días Disponibilidad Papeles"] = (df_t["Fecha Disponibilidad Papeles"] - df_t["Fecha de Patentamiento"]).dt.days
        df_t["Días para Entrega (Post-Arribo)"] = (df_t["Fecha de confirmacion de entrega"] - df_t["Fecha Arribo"]).dt.days
        df_t["Ciclo Total (Fact-Entrega)"] = (df_t["Fecha de confirmacion de entrega"] - df_t["Fecha de Facturacion"]).dt.days

        # Métricas de tiempo promedio
        mt1, mt2, mt3, mt4 = st.columns(4)
        mt1.metric("Prom. Logística", f"{df_t['Días Logística (Pedido-Arribo)'].mean():.1f} d")
        mt2.metric("Prom. Patentamiento", f"{df_t['Días Patentamiento'].mean():.1f} d")
        mt3.metric("Prom. Entrega Real", f"{df_t['Días para Entrega (Post-Arribo)'].mean():.1f} d")
        mt4.metric("Ciclo Total Prom.", f"{df_t['Ciclo Total (Fact-Entrega)'].mean():.1f} d")

        st.divider()
        
        # Gráfico comparativo
        st.write("### Ciclo Total de Entrega por Vendedor (Días)")
        if "Vendedor" in df_t.columns:
            v_time = df_t.groupby("Vendedor")["Ciclo Total (Fact-Entrega)"].mean().sort_values().reset_index()
            fig_t = px.bar(v_time, x="Vendedor", y="Ciclo Total (Fact-Entrega)", color="Ciclo Total (Fact-Entrega)", 
                           color_continuous_scale="RdYlGn_r", template="plotly_white")
            st.plotly_chart(fig_t, use_container_width=True)

        st.subheader("📋 Detalle de Tiempos por Unidad")
        cols_t_view = ["Vendedor", "Cliente", "Chasis", "Días Logística (Pedido-Arribo)", "Días Patentamiento", "Días para Entrega (Post-Arribo)", "Ciclo Total (Fact-Entrega)"]
        st.dataframe(df_t[cols_t_view].dropna(subset=["Ciclo Total (Fact-Entrega)"]), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 3: ANÁLISIS VISUAL
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
