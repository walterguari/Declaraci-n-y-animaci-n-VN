import streamlit as st
from streamlit.connections import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Portal Análisis DUV WG", layout="wide", page_icon="🚗")

st.title("🚗 Control de Unidades - Análisis DUV")

# 2. Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. URL de la planilla (Link que me pasaste)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # --- LA SOLUCIÓN ---
    # Usamos query para forzar la lectura de la hoja específica evitando el error de URL
    # Esto lee la pestaña "ANALISIS DUV WG" de forma más robusta
    df = conn.read(
        spreadsheet=url, 
        worksheet="ANALISIS DUV WG", 
        ttl="0" # Forzamos a que no use caché vieja con errores
    )
    
    # Limpiamos filas vacías
    df = df.dropna(how='all')

    # --- Interfaz ---
    st.sidebar.header("Control")
    operador = st.sidebar.text_input("Operador auditado:")
    
    # Buscador inteligente
    busqueda = st.text_input("🔍 Buscar por cualquier dato (Vendedor, Modelo, Chasis, Cliente):")
    
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    # Mostrar Tabla
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Métricas
    st.divider()
    st.metric("Total Unidades", len(df_display))

except Exception as e:
    st.error("Error crítico de URL detectado.")
    st.info("Si el error persiste, la solución más rápida es cambiar el nombre de la pestaña en Google Sheets a 'ANALISIS_DUV_WG' (con guiones bajos) y actualizarlo en el código.")
    with st.expander("Detalle del error"):
        st.write(e)
