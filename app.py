import streamlit as st
from streamlit.connections import GSheetsConnection
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Portal Análisis DUV", layout="wide", page_icon="🚗")

st.title("🚗 Control de Unidades - Análisis DUV")

# Conexión directa
conn = st.connection("gsheets", type=GSheetsConnection)

# URL específica de la hoja (usando el gid que me pasaste)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # Leemos los datos sin especificar el nombre de la hoja, 
    # ya que el GID en la URL ya le dice a Google qué hoja abrir.
    df = conn.read(spreadsheet=url)
    
    # Limpiamos filas vacías
    df = df.dropna(how='all')

    # --- BARRA LATERAL ---
    st.sidebar.header("Control de Auditoría")
    operador = st.sidebar.text_input("Operador auditado:", placeholder="Tu nombre...")
    if operador:
        st.sidebar.success(f"Sesión: {operador}")

    # --- BUSCADOR ---
    st.subheader("Búsqueda de Datos")
    busqueda = st.text_input("🔍 Filtrar por Vendedor, Modelo, Cliente o Chasis:")
    
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    # Mostrar tabla
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Métricas al pie
    st.divider()
    st.metric("Total Unidades en Lista", len(df_display))

except Exception as e:
    st.error("Error de conexión con la planilla.")
    st.info("Asegúrate de que el acceso sea 'Cualquier persona con el enlace puede ver'.")
    with st.expander("Detalle técnico"):
        st.write(e)
