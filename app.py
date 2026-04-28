import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Gestión de Hand Over y Garantías")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Listado de columnas ajustado
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
    df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
    df["Fecha de Hand over"] = pd.to_datetime(df["Fecha de Hand over"], errors='coerce')
    
    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    
    # Unidades con Patentamiento (Para los botones de meses)
    df_con_patente = df.dropna(subset=["Fecha de Patentamiento"]).copy()
    df_con_patente["Mes_Display"] = df_con_patente["Fecha de Patentamiento"].dt.strftime('%b %Y')

    # --- SIDEBAR (FILTROS) ---
    st.sidebar.header("Filtros de Categoría")
    canales = sorted(df["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)
    
    vendedores = sorted(df["Vendedor"].dropna().unique()) if "Vendedor" in df.columns else []
    filtro_vendedor = st.sidebar.multiselect("Vendedor", options=vendedores)

    # --- BOTONES SUPERIORES: MESES ---
    st.write("### 📅 Meses con Hand Over Pendientes")
    meses_pendientes = df_con_patente[~df_con_patente['TIENE_HO']].sort_values("Fecha de Patentamiento")
    opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()

    if opciones_meses:
        mes_sel = st.pills("Seleccioná un mes para auditar:", ["Todos"] + opciones_meses, default="Todos")
    else:
        st.success("✅ ¡Todo al día! No hay pendientes con fecha de patentamiento.")
        mes_sel = "Todos"

    # --- BOTONES SUPERIORES: ESTADO INTERNO ---
    st.write("### 🏷️ Filtrar por Estado Interno")
    col_ei = "ESTADO INTERNO"
    if col_ei in df.columns:
        # Limpieza segura: convertimos a texto, quitamos nulos y espacios
        df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()
        # Filtramos para que no aparezcan 'nan' ni vacíos en los botones
        estados_lista = sorted([e for e in df[col_ei].unique() if e.upper() not in ["NAN", "", "NONE"]])
        ei_sel = st.pills("Seleccioná una categoría interna:", ["Todos"] + estados_lista, default="Todos")
    else:
        ei_sel = "Todos"

    # --- FILTRADO DE DATOS FINAL ---
    df_f = df.copy()
    
    if mes_sel != "Todos":
        df_f = df_f[df_f["Fecha de Patentamiento"].dt.strftime('%b %Y') == mes_sel]
    
    if ei_sel != "Todos":
        df_f = df_f[df_f[col_ei] == ei_sel]
        
    if filtro_canal:
        df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
        
    if filtro_vendedor:
        df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

    # --- MÉTRICAS ---
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    patentados_vista = df_f[df_f["Fecha de Patentamiento"].notna()]
    entregados_vista = df_f[df_f["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
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
    st.subheader(f"📋 Detalle: {mes_sel} | {ei_sel}")
    modo_tabla = st.radio("Mostrar en tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
    
    df_final = faltan_ho_vista if modo_tabla == "Solo Pendientes ⚠️" else df_f

    busqueda = st.text_input("🔍 Buscar por Chasis, Cliente o Vendedor:")
    if busqueda:
        mask = df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_final = df_final[mask]

    cols_existentes = [c for c in COLUMNAS_MOSTRAR if c in df_final.columns]
    st.dataframe(df_final[cols_existentes], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al procesar el tablero.")
    st.write(f"Detalle técnico: {e}")
