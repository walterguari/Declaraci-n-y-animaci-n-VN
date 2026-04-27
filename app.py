import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuración
st.set_page_config(page_title="Análisis DUV WG", layout="wide")

st.title("📊 Portal de Gestión - Análisis DUV")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# URL Limpia (sin espacios ni caracteres raros)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # Leemos la hoja quitando cualquier espacio accidental en el nombre
    df = conn.read(spreadsheet=url, worksheet="ANALISIS DUV WG")
    
    # Barra lateral
    st.sidebar.header("Auditoría")
    operador = st.sidebar.text_input("Operador auditado:")
    if operador:
        st.sidebar.success(f"Operador: {operador}")

    # Buscador y Tabla
    busqueda = st.text_input("🔍 Buscar unidad, asesor o cliente:")
    if busqueda:
        df = df[df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)]

    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error de conexión.")
    st.info("Revisá que la pestaña en Google Sheets se llame exactamente 'ANALISIS DUV WG' sin espacios al final.")
    st.write(e)
