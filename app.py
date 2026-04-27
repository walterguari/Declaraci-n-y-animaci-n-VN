import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de la página para que se vea bien en monitores y tablets
st.set_page_config(page_title="Portal de Análisis DUV", layout="wide")

st.title("📊 Portal de Gestión - Análisis DUV")

# 1. Conexión con la planilla
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Lectura de los datos usando la URL y el nombre de la hoja que pasaste
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # IMPORTANTE: Aquí usamos el nombre exacto de la pestaña
    df = conn.read(spreadsheet=url, worksheet="ANALISIS DUV WG")
    
    # Limpiamos filas vacías si las hay
    df = df.dropna(how='all')

    # --- BARRA LATERAL (Filtros y Auditoría) ---
    st.sidebar.header("Control de Auditoría")
    
    # Campo para escribir el nombre del operador directamente (sin sugerencias)
    operador = st.sidebar.text_input("Operador auditado:")
    
    if operador:
        st.sidebar.success(f"Sesión iniciada: {operador}")

    st.sidebar.divider()
    
    # Filtro por columna (Asumiendo que hay una columna de Vendedor o Estado)
    # Podés ajustar los nombres de las columnas según lo que veas en tu Excel
    columnas = df.columns.tolist()
    st.sidebar.subheader("Filtros rápidos")
    filtro_col = st.sidebar.selectbox("Filtrar por:", ["Mostrar todo"] + columnas)
    
    if filtro_col != "Mostrar todo":
        valor_filtro = st.sidebar.text_input(f"Buscar en {filtro_col}:")
        if valor_filtro:
            df = df[df[filtro_col].astype(str).str.contains(valor_filtro, case=False)]

    # --- CUERPO PRINCIPAL ---
    st.subheader("Visualización de Datos")
    
    # Buscador general
    busqueda_general = st.text_input("🔍 Búsqueda rápida de unidades, clientes o fechas:")
    if busqueda_general:
        df = df[df.apply(lambda row: row.astype(str).str.contains(busqueda_general, case=False).any(), axis=1)]

    # Mostrar la tabla
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Métricas rápidas (Ejemplo: Total de unidades)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Registros", len(df))

except Exception as e:
    st.error("Error al conectar con la pestaña 'ANALISIS DUV WG'.")
    st.info("Aseguráte de que el nombre de la pestaña en Google Sheets no tenga espacios extra al final.")
    st.write(e)
