import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuración de página
st.set_page_config(page_title="Portal Animación VN", layout="wide")

st.title("🚗 Seguimiento de Unidades - Animación VN")

# Conexión a la base de Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Cargamos los datos (usando el link que me pasaste)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # Leemos la hoja (si el nombre de la pestaña no es Sheet1, cambialo aquí)
    df = conn.read(spreadsheet=url, worksheet="Sheet1")
    
    # --- Barra Lateral ---
    st.sidebar.header("Gestión de Auditoría")
    
    # Opción para escribir el nombre directamente
    operador = st.sidebar.text_input("Nombre del Operador auditado:")
    
    if operador:
        st.sidebar.success(f"Operador: {operador}")

    # --- Filtros de la Tabla ---
    st.subheader("Datos de la Planilla")
    busqueda = st.text_input("Buscar por cliente, unidad o asesor:")
    
    if busqueda:
        # Filtra en todas las columnas que contengan el texto buscado
        df = df[df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)]

    # Mostramos la tabla interactiva
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("No se pudo conectar con la planilla. Verificá que el link sea público o las credenciales.")
    st.write(e)
