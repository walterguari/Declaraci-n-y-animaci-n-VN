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

    # --- PROCESAMIENTO DE FECHAS ---
    if "Fecha de Patentamiento" in df.columns:
        df["Fecha de Patentamiento"] = pd.to_datetime(df["Fecha de Patentamiento"], errors='coerce')
        # Crear columna de Mes/Año para los botones
        df["Mes_Patentamiento"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
        meses_disponibles = sorted(df["Mes_Patentamiento"].dropna().unique(), 
                                   key=lambda x: pd.to_datetime(x, format='%b %Y'))
    else:
        meses_disponibles = []

    if "Fecha de Hand over" in df.columns:
        df['TIENE_GARANTIA'] = pd.to_datetime(df["Fecha de Hand over"], errors='coerce').notna()
    else:
        df['TIENE_GARANTIA'] = False

    # --- SIDEBAR (FILTROS IZQUIERDA) ---
    st.sidebar.header("Filtros Avanzados")
    
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=df["Canal de Venta"].unique()) if "Canal de Venta" in df.columns else []
    filtro_vendedor = st.sidebar.multiselect("Vendedor", options=df["Vendedor"].unique()) if "Vendedor" in df.columns else []
    filtro_marca = st.sidebar.multiselect("Marca", options=df["Marca"].unique()) if "Marca" in df.columns else []

    # --- BOTONES SUPERIORES (MESES) ---
    st.write("### Seleccionar Mes de Patentamiento")
    if meses_disponibles:
        # Añadimos opción "Todos los meses"
        opciones_mes = ["Todos"] + meses_disponibles
        mes_seleccionado = st.pills("Meses detectados:", opciones_mes, default="Todos")
    else:
        mes_seleccionado = "Todos"

    # --- LÓGICA DE FILTRADO ---
    df_filtrado = df.copy()

    if mes_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Mes_Patentamiento"] == mes_seleccionado]
    
    if filtro_canal:
        df_filtrado = df_filtrado[df_filtrado["Canal de Venta"].isin(filtro_canal)]
    
    if filtro_vendedor:
        df_filtrado = df_filtrado[df_filtrado["Vendedor"].isin(filtro_vendedor)]
        
    if filtro_marca:
        df_filtrado = df_filtrado[df_filtrado["Marca"].isin(filtro_marca)]

    # --- MÉTRICAS ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    
    entregados = df_filtrado[df_filtrado["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)] if "Estado" in df_filtrado.columns else pd.DataFrame()
    pendientes = entregados[~entregados['TIENE_GARANTIA']]
    
    m1.metric("Unidades en Vista", len(df_filtrado))
    m2.metric("Pendientes Hand Over", len(pendientes), delta_color="inverse")
    
    eficiencia = (len(entregados[entregados['TIENE_GARANTIA']]) / len(entregados) * 100) if len(entregados) > 0 else 0
    m3.metric("Eficacia Vista Actual", f"{eficiencia:.1f}%")

    # --- VISTA DE TABLA ---
    st.subheader("📋 Listado Detallado")
    
    # Filtro rápido de Garantía (Botones rápidos)
    modo_ho = st.radio("Estado de Garantía:", ["Todos", "⚠️ Solo Pendientes", "✅ Completados"], horizontal=True)
    
    if modo_ho == "⚠️ Solo Pendientes":
        df_final = pendientes
    elif modo_ho == "✅ Completados":
        df_final = entregados[entregados['TIENE_GARANTIA']]
    else:
        df_final = df_filtrado

    # Columnas finales
    cols_presentes = [c for c in COLUMNAS_MOSTRAR if c in df_final.columns]
    st.dataframe(df_final[cols_presentes], use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al configurar los filtros.")
    st.write(e)
