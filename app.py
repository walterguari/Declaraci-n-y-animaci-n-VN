import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Gestión de Hand Over y Garantías")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

COLUMNAS_MOSTRAR = [
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

    # --- PROCESAMIENTO INICIAL ---
    df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
    df["Fecha de Hand over"] = pd.to_datetime(df["Fecha de Hand over"], errors='coerce')
    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    
    # Columna de visualización de mes
    df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    # Limpieza de Estado Interno
    col_ei = "ESTADO INTERNO"
    df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()

    # --- SIDEBAR (FILTROS FIJOS) ---
    st.sidebar.header("Filtros de Categoría")
    canales = sorted(df["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)
    
    vendedores = sorted(df["Vendedor"].dropna().unique()) if "Vendedor" in df.columns else []
    filtro_vendedor = st.sidebar.multiselect("Vendedor", options=vendedores)

    # --- PASO 1: FILTRO DE MESES (LOS QUE TIENEN PENDIENTES) ---
    st.write("### 📅 1. Seleccioná el Mes con Pendientes")
    meses_pendientes = df[~df['TIENE_HO']].dropna(subset=["Fecha de Patentamiento"]).sort_values("Fecha de Patentamiento")
    opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()

    if opciones_meses:
        mes_sel = st.pills("Meses detectados:", ["Todos"] + opciones_meses, default="Todos", key="pills_meses")
    else:
        st.success("✅ No hay meses con Hand Over pendientes.")
        mes_sel = "Todos"

    # --- PASO 2: FILTRO DINÁMICO DE ESTADO INTERNO (INTERACTIVO) ---
    st.write("### 🏷️ 2. Filtrar por Estado Interno (Solo pendientes)")
    
    # Filtramos el dataframe temporalmente para ver qué Estados Internos hay según el mes elegido
    df_temp_ei = df[~df['TIENE_HO']].copy() # Solo lo que no tiene HO
    if mes_sel != "Todos":
        df_temp_ei = df_temp_ei[df_temp_ei["Mes_Display"] == mes_sel]
    
    # Obtenemos la lista de estados que REALMENTE existen en esa selección
    estados_disponibles = sorted([e for e in df_temp_ei[col_ei].unique() if e.upper() not in ["NAN", "", "NONE"]])

    if estados_disponibles:
        ei_sel = st.pills("Categorías con pendientes en este periodo:", ["Todos"] + estados_disponibles, default="Todos", key="pills_ei")
    else:
        st.info("No hay estados internos específicos para esta selección.")
        ei_sel = "Todos"

    # --- FILTRADO FINAL DE LA TABLA Y MÉTRICAS ---
    df_f = df.copy()
    if mes_sel != "Todos":
        df_f = df_f[df_f["Mes_Display"] == mes_sel]
    if ei_sel != "Todos":
        df_f = df_f[df_f[col_ei] == ei_sel]
    if filtro_canal:
        df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
    if filtro_vendedor:
        df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

    # --- MÉTRICAS ---
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    patentados_v = df_f[df_f["Fecha de Patentamiento"].notna()]
    entregados_v = df_f[df_f["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
    faltan_ho_v = patentados_v[~patentados_v['TIENE_HO']]
    
    c1.metric("Patentados", len(patentados_v))
    c2.metric("Entregados", len(entregados_v))
    c3.metric("Faltan Hand Over", len(faltan_ho_v), delta_color="inverse")
    eficacia = (len(patentados_v[patentados_v['TIENE_HO']]) / len(patentados_v) * 100) if len(patentados_v) > 0 else 0
    c4.metric("% Eficacia", f"{eficacia:.1f}%")

    # --- TABLA ---
    st.subheader(f"📋 Listado: {mes_sel} | {ei_sel}")
    modo_tabla = st.radio("Filtro rápido de tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
    
    df_final = faltan_ho_v if modo_tabla == "Solo Pendientes ⚠️" else df_f
    
    busqueda = st.text_input("🔍 Búsqueda rápida (Chasis, Cliente, etc.):")
    if busqueda:
        mask = df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_final = df_final[mask]

    cols_existentes = [c for c in COLUMNAS_MOSTRAR if c in df_final.columns]
    st.dataframe(df_final[cols_existentes], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error en la interactividad de los filtros.")
    st.write(f"Detalle: {e}")
