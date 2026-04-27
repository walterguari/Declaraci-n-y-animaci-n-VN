import streamlit as st
from streamlit.connections import GSheetsConnection
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Portal Análisis DUV", layout="wide")

st.title("🚗 Control de Unidades - Análisis DUV")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# URL de la planilla
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # Leemos los datos. 
    # Si da error con 'worksheet', intentamos leer la primera hoja por defecto
    df = conn.read(spreadsheet=url, worksheet="ANALISIS DUV WG")
    
    # Limpieza básica
    df = df.dropna(how='all')

    # --- BARRA LATERAL ---
    st.sidebar.header("Gestión de Auditoría")
    
    # Opción para escribir nombre directamente (sin sugerencias)
    operador = st.sidebar.text_input("Operador auditado:")
    if operador:
        st.sidebar.success(f"Sesión: {operador}")

    # --- CUERPO PRINCIPAL ---
    # Buscador general
    busqueda = st.text_input("🔍 Buscar por Cliente, Vendedor o Chasis:")
    
    if busqueda:
        # Filtro inteligente en todas las columnas
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_filtrado = df[mask]
    else:
        df_filtrado = df

    # Mostrar tabla
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # Métricas al pie
    st.divider()
    st.metric("Total de Unidades en Pantalla", len(df_filtrado))

except Exception as e:
    st.error("Hubo un problema al cargar la hoja 'ANALISIS DUV WG'.")
    st.info("Revisá que el nombre de la pestaña en el Excel sea exactamente ese, sin espacios extra.")
    st.write("Detalle técnico:", e)
