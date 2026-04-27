import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Gestión de Hand Over y Garantías")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Columnas solicitadas
COLUMNAS_MOSTRAR = [
    "Canal de Venta", "Vendedor", "Cliente", "Teléfono", "E-mail", 
    "Chasis", "Marca", "Modelo", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado de Unidad por Administración/Mayorista", "Estado", 
    "Fecha de confirmacion de entrega", "Encuesta Temprana", 
    "Comentario Enc. Temp.", "EI - Reco", "Comentario de la Encuesta interna", 
    "EI - CSI", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    df_raw = conn.read(spreadsheet=url_base)
    df = df_raw.dropna(how='all')
    df.columns = [str(c).strip() for c in df.columns]

    # --- PROCESAMIENTO DE LÓGICA DE CONTROL ---
    if "Fecha de Patentamiento" in df.columns:
        df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
        df["Mes_Año"] = df["Fecha de Patentamiento"].dt.strftime('%m-%Y') # Formato para ordenar
        df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    
    # Definición de Garantía (True si tiene fecha, False si está vacío)
    col_ho = "Fecha de Hand over"
    df['TIENE_HO'] = pd.to_datetime(df[col_ho], errors='coerce').notna() if col_ho in df.columns else False
    
    # Definición de Entregado
    df['ES_ENTREGADO'] = df["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False) if "Estado" in df.columns else False

    # --- FILTRO DE MESES CON PENDIENTES ---
    # Solo mostramos meses donde hay al menos una unidad Patentada que NO tiene Hand Over
    meses_con_pendientes = df[~df['TIENE_HO']].sort_values("Fecha de Patentamiento")
    opciones_meses = meses_con_pendientes["Mes_Display"].unique().tolist()

    # --- SIDEBAR (FILTROS IZQUIERDA) ---
    st.sidebar.header("Filtros de Categoría")
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=sorted(df["Canal de Venta"].dropna().unique())) if "Canal de Venta" in df.columns else []
    filtro_vendedor = st.sidebar.multiselect("Vendedor", options=sorted(df["Vendedor"].dropna().unique())) if "Vendedor" in df.columns else []

    # --- BOTONES SUPERIORES (SOLO MESES CON PENDIENTES) ---
    st.write("### 📅 Meses con Hand Over Pendientes")
    if opciones_meses:
        mes_sel = st.pills("Seleccioná un mes para auditar:", ["Todos"] + opciones_meses, default="Todos")
    else:
        st.success("✅ ¡Increíble! No se detectan meses con Hand Over pendientes.")
        mes_sel = "Todos"

    # --- LÓGICA DE FILTRADO FINAL ---
    df_f = df.copy()
    if mes_sel != "Todos":
        df_f = df_f[df_f["Mes_Display"] == mes_sel]
    if filtro_canal:
        df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
    if filtro_vendedor:
        df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

    # --- MÉTRICAS DINÁMICAS ---
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    
    # Cálculos sobre la vista actual
    total_patentados = len(df_f)
    total_entregados = len(df_f[df_f['ES_ENTREGADO']])
    faltan_ho = len(df_f[~df_f['TIENE_HO']]) # Todos los que no tienen fecha
    
    with c1:
        st.metric("Patentados", total_patentados)
    with c2:
        st.metric("Entregados", total_entregados)
    with c3:
        st.metric("Faltan Hand Over", faltan_ho, delta="Acción requerida" if faltan_ho > 0 else None, delta_color="inverse")
    with c4:
        eficacia = (len(df_f[df_f['TIENE_HO']]) / total_patentados * 100) if total_patentados > 0 else 0
        st.metric("% Eficacia", f"{eficacia:.1f}%")

    # --- TABLA DETALLADA ---
    st.subheader(f"📋 Detalle de Unidades - {mes_sel}")
    
    # Selector rápido de tabla
    modo_tabla = st.radio("Mostrar:", ["Solo Pendientes ⚠️", "Todos los del mes"], horizontal=True)
    
    if modo_tabla == "Solo Pendientes ⚠️":
        df_final = df_f[~df_f['TIENE_HO']]
    else:
        df_final = df_f

    # Columnas finales
    cols_existentes = [c for c in COLUMNAS_MOSTRAR if c in df_final.columns]
    st.dataframe(df_final[cols_existentes], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al procesar el tablero dinámico.")
    st.write(e)
