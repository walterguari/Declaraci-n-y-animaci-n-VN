import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Gestión de Hand Over y Garantías")

# 2. Conexión
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Columnas finales a mostrar
COLUMNAS_MOSTRAR = [
    "Vendedor", "Cliente", "Teléfono", "E-mail", 
    "Chasis", "Marca", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado", "Fecha de confirmacion de entrega", "Encuesta Temprana", 
    "Comentario Enc. Temp.", "EI - Reco", "Comentario de la Encuesta interna", 
    "EI - CSI", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    df_raw = conn.read(spreadsheet=url_base)
    df = df_raw.dropna(how='all')
    df.columns = [str(c).strip() for c in df.columns]

    # --- LIMPIEZA DE FECHAS ---
    if "Fecha de Patentamiento" in df.columns:
        df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
        # Filtramos solo las que SI tienen fecha para el display de meses
        df_con_fecha = df.dropna(subset=["Fecha de Patentamiento"])
        df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    
    # Lógica de Hand Over (Solo contamos los que realmente están vacíos)
    col_ho = "Fecha de Hand over"
    df['TIENE_HO'] = pd.to_datetime(df[col_ho], errors='coerce').notna() if col_ho in df.columns else False
    df['ES_ENTREGADO'] = df["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False) if "Estado" in df.columns else False

    # --- FILTRO DE MESES (QUITANDO EL 'nan') ---
    # Solo meses de unidades que no tienen HO y que tienen una fecha válida
    meses_pendientes = df[~df['TIENE_HO']].dropna(subset=["Fecha de Patentamiento"]).sort_values("Fecha de Patentamiento")
    opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()

    # --- SIDEBAR ---
    st.sidebar.header("Filtros de Categoría")
    canal_opciones = sorted(df["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canal_opciones)
    vendedor_opciones = sorted(df["Vendedor"].dropna().unique()) if "Vendedor" in df.columns else []
    filtro_vendedor = st.sidebar.multiselect("Vendedor", options=vendedor_opciones)

    # --- BOTONES SUPERIORES ---
    st.write("### 📅 Meses con Hand Over Pendientes")
    if opciones_meses:
        # Eliminamos cualquier valor nulo de la lista de botones
        mes_sel = st.pills("Seleccioná un mes para auditar:", ["Todos"] + [m for m in opciones_meses if str(m) != 'nan'], default="Todos")
    else:
        st.success("✅ ¡Al día! No hay pendientes con fecha de patentamiento.")
        mes_sel = "Todos"

    # --- FILTRADO FINAL ---
    df_f = df.copy()
    if mes_sel != "Todos":
        df_f = df_f[df_f["Mes_Display"] == mes_sel]
    if filtro_canal:
        df_f = df_f[df_f["Canal de Venta"].isin(filtro_canal)]
    if filtro_vendedor:
        df_f = df_f[df_f["Vendedor"].isin(filtro_vendedor)]

    # --- MÉTRICAS ---
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    
    # Patentados: Todos los que tienen una fecha de patentamiento válida en la vista
    val_patentados = df_f.dropna(subset=["Fecha de Patentamiento"])
    
    with c1:
        st.metric("Patentados", len(val_patentados))
    with c2:
        st.metric("Entregados", len(df_f[df_f['ES_ENTREGADO']]))
    with c3:
        # Faltan HO: Son los que NO tienen fecha de Hand Over cargada
        n_faltan = len(df_f[~df_f['TIENE_HO']])
        st.metric("Faltan Hand Over", n_faltan, delta="Acción requerida" if n_faltan > 0 else None, delta_color="inverse")
    with c4:
        # Eficacia: (Unidades con HO / Total Patentados)
        n_con_ho = len(df_f[df_f['TIENE_HO']])
        eficacia = (n_con_ho / len(val_patentados) * 100) if len(val_patentados) > 0 else 0
        st.metric("% Eficacia", f"{eficacia:.1f}%")

    # --- TABLA ---
    st.subheader(f"📋 Detalle de Unidades - {mes_sel}")
    modo = st.radio("Mostrar:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
    
    df_tab = df_f[~df_f['TIENE_HO']] if modo == "Solo Pendientes ⚠️" else df_f
    
    cols_finales = [c for c in COLUMNAS_MOSTRAR if c in df_tab.columns]
    st.dataframe(df_tab[cols_existentes], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al procesar el tablero.")
    st.write(e)
