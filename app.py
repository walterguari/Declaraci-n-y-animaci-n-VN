import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Gestión de Hand Over y Garantías")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Listado de columnas ajustado (sin Canal, Modelo ni Mayorista)
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

    # --- PROCESAMIENTO DE FECHAS Y LOGICA ---
    # Convertimos Fecha de Patentamiento y Hand Over a formato fecha
    df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
    df["Fecha de Hand over"] = pd.to_datetime(df["Fecha de Hand over"], errors='coerce')
    
    # Unidades con Hand Over cargado (Garantía OK)
    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    
    # Unidades con Patentamiento (Para evitar el 'nan' en los botones)
    df_con_patente = df.dropna(subset=["Fecha de Patentamiento"]).copy()
    df_con_patente["Mes_Display"] = df_con_patente["Fecha de Patentamiento"].dt.strftime('%b %Y')

    # --- SIDEBAR (FILTROS) ---
    st.sidebar.header("Filtros de Categoría")
    # El filtro de Canal de Venta sigue funcionando aunque no esté en la tabla
    canales = sorted(df["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)
    
    vendedores = sorted(df["Vendedor"].dropna().unique()) if "Vendedor" in df.columns else []
    filtro_vendedor = st.sidebar.multiselect("Vendedor", options=vendedores)

    # --- BOTONES SUPERIORES (QUITANDO 'nan') ---
    st.write("### 📅 Meses con Hand Over Pendientes")
    
    # Obtenemos meses SOLO de unidades que no tienen HO y que tienen fecha de patentamiento válida
    meses_pendientes = df_con_patente[~df_con_patente['TIENE_HO']].sort_values("Fecha de Patentamiento")
    opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()

    if opciones_meses:
        mes_sel = st.pills("Seleccioná un mes para auditar:", ["Todos"] + opciones_meses, default="Todos")
    else:
        st.success("✅ ¡Todo al día! No se detectan meses con pendientes de Hand Over.")
        mes_sel = "Todos"

    # --- FILTRADO DE DATOS ---
    df_f = df.copy()
    
    # Aplicar filtro de mes (usando la transformación de fecha)
    if mes_sel != "Todos":
        df_f = df_f[df_f["Fecha de Patentamiento"].dt.strftime('%b %Y') == mes_sel]
    
    # Aplicar filtros de sidebar
    if filtro_canal:
        df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
    if filtro_vendedor:
        df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

    # --- MÉTRICAS ---
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    
    # Patentados: Unidades que tienen fecha de patentamiento en la selección actual
    patentados_vista = df_f[df_f["Fecha de Patentamiento"].notna()]
    # Entregados: Unidades con estado 'ENTREGADO'
    entregados_vista = df_f[df_f["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
    # Faltan HO: Patentados que NO tienen fecha de Hand Over
    faltan_ho_vista = patentados_vista[~patentados_vista['TIENE_HO']]
    
    with c1:
        st.metric("Patentados", len(patentados_vista))
    with c2:
        st.metric("Entregados", len(entregados_vista))
    with c3:
        st.metric("Faltan Hand Over", len(faltan_ho_vista), 
                  delta="Acción requerida" if len(faltan_ho_vista) > 0 else None, 
                  delta_color="inverse")
    with c4:
        eficacia = (len(patentados_vista[patentados_vista['TIENE_HO']]) / len(patentados_vista) * 100) if len(patentados_vista) > 0 else 0
        st.metric("% Eficacia", f"{eficacia:.1f}%")

    # --- TABLA DETALLADA ---
    st.subheader(f"📋 Detalle de Unidades - {mes_sel}")
    modo_tabla = st.radio("Mostrar en tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
    
    if modo_tabla == "Solo Pendientes ⚠️":
        df_final = faltan_ho_vista
    else:
        df_final = df_f

    # Buscador manual
    busqueda = st.text_input("🔍 Buscar por Chasis, Cliente o Vendedor:")
    if busqueda:
        mask = df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_final = df_final[mask]

    # Columnas finales
    cols_existentes = [c for c in COLUMNAS_MOSTRAR if c in df_final.columns]
    st.dataframe(df_final[cols_existentes], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al procesar el tablero.")
    st.write(e)
