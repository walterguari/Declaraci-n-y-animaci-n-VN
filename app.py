import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Portal Análisis DUV WG", layout="wide", page_icon="🚗")

st.title("🚗 Control de Unidades - Análisis DUV")

# 2. Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. URL DIRECTA A LA HOJA (Usamos el GID al final para evitar errores de nombre)
# El link ya termina en #gid=1482583153, que es la hoja ANALISIS DUV WG
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # 4. LECTURA SIMPLIFICADA
    # Al no pasarle el parámetro 'worksheet', la librería lee la pestaña que indica el GID de la URL.
    # Esto evita CUALQUIER error de espacios o caracteres especiales.
    df = conn.read(spreadsheet=url_base)
    
    # Limpiamos filas vacías
    df = df.dropna(how='all')

    # --- BARRA LATERAL ---
    st.sidebar.header("Gestión")
    operador = st.sidebar.text_input("Operador auditado:", placeholder="Tu nombre...")
    if operador:
        st.sidebar.success(f"Operador: {operador}")

    # --- BUSCADOR ---
    busqueda = st.text_input("🔍 Buscar por cualquier campo (Vendedor, Cliente, Chasis...):")
    
    if busqueda:
        # Filtro inteligente
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    # --- MOSTRAR DATOS ---
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Métricas
    st.divider()
    st.metric("Total Unidades en Pantalla", len(df_display))

except Exception as e:
    st.error("No se pudo conectar con la planilla.")
    st.info("Revisá que el acceso en Google Sheets sea 'Cualquier persona con el enlace puede ver'.")
    with st.expander("Detalle del error técnico"):
        st.write(e)
