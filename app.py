import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Portal Análisis DUV WG", layout="wide")

st.title("🚗 Seguimiento de Unidades - Análisis DUV")

# 2. Establecer conexión
# Usamos la sintaxis estándar que requiere la librería st-gsheets-connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. URL y Nombre de hoja (Copiado de tu link y captura)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"
nombre_hoja = "ANALISIS DUV WG"

try:
    # 4. Lectura de datos
    df = conn.read(spreadsheet=url, worksheet=nombre_hoja)
    
    # Limpieza de filas vacías
    df = df.dropna(how='all')

    # --- Interfaz Lateral ---
    st.sidebar.header("Control de Auditoría")
    operador = st.sidebar.text_input("Operador auditado:", placeholder="Tu nombre aquí...")
    
    if operador:
        st.sidebar.success(f"Operador: {operador}")

    # --- Buscador y Tabla ---
    st.subheader("Base de Datos en Tiempo Real")
    busqueda = st.text_input("🔍 Buscar por cualquier campo (Vendedor, Cliente, Chasis...):")
    
    if busqueda:
        # Filtro global inteligente
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    # Mostrar la tabla
    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    # Métricas
    st.divider()
    st.metric("Total Unidades Encontradas", len(df_mostrar))

except Exception as e:
    st.error(f"Error al conectar con la hoja '{nombre_hoja}'")
    st.info("Asegúrate de que el archivo de Google Sheets sea público ('Cualquier persona con el enlace puede ver').")
    with st.expander("Detalles del error"):
        st.write(e)
